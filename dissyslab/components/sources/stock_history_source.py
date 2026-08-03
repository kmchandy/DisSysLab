# dissyslab/components/sources/stock_history_source.py

"""
StockHistorySource: Emits full daily OHLCV price history for one or
more tickers, fetched once from Stooq's free historical-data CSV
endpoint (https://stooq.com/q/d/l/).

This is the bulk, one-shot counterpart to ``StocksSource``
(``stocks_source.py``), which polls Stooq's *live quote* endpoint
(``/q/l/``) repeatedly for one ticker's current price. A backtest
needs the opposite shape: many tickers, many years of daily bars,
fetched once at startup rather than polled — so this is a distinct
class and a distinct registry entry (``stock_history``), not a mode
of ``StocksSource``.

Each ticker's history is a list of daily bars:
    {
        "date":   "2024-01-02",
        "open":   185.10,
        "high":   188.30,
        "low":    184.90,
        "close":  187.42,
        "volume": 58414500,
    }

``run()`` is a one-shot generator (like ``starter_source.Starter``):
it fetches every requested ticker in turn, then yields exactly ONE
bulk message and stops. That single-message shape is deliberate — a
downstream coordinator (e.g. a ``merge_synch`` JOIN pairing this
source with a strategy-designer branch) waits for "one message from
each" input; a source that trickled out one message per ticker would
break that pairing. The message looks like:
    {
        "type":    "stock_history",
        "tickers": ["AAPL", "MSFT", ...],
        "start":   "2015-01-01",
        "end":     "2025-01-01",
        "history": {
            "AAPL": [ {date, open, high, low, close, volume}, ... ],
            "MSFT": [ ... ],
            ...
        },
        "errors": {
            # present only for tickers Stooq could not serve, e.g.:
            "BAD.T": "Stooq returned no data for 'bad.t.us'.",
        },
        "timestamp": "2026-07-28T21:34:56+00:00",
    }

Usage:
    from dissyslab.components.sources.stock_history_source import StockHistorySource
    from dissyslab.blocks import Source

    history = StockHistorySource(
        tickers=["AAPL", "MSFT", "GOOGL"],
        start="2015-01-01",
        end="2025-01-01",
    )
    source = Source(fn=history.run, name="price_history")

Design notes:
    - No API key, no signup — same as ``stocks_source.py``. Stooq's
      historical endpoint is plain CSV over HTTP.
    - One ticker per HTTP request; Stooq has no bulk "all these
      tickers in one call" endpoint. For ~100 SP100 tickers this is
      ~100 requests, made in sequence with a small pause between them
      (``request_pause``, default 0.25s) to be a polite, non-hammering
      client rather than because Stooq is known to rate-limit.
    - A ticker Stooq can't serve (typo, delisted, market closed with
      no history) does NOT crash the whole fetch. Its error is
      recorded under ``errors[ticker]`` and every other ticker's data
      still comes through — matching ``StocksSource``'s
      "errors surface as data, the pipeline stays alive" convention.
    - Uses the same ``.us``-suffix normalization as ``StocksSource``
      for bare US tickers; pass a full Stooq symbol (e.g. "ntt.jp")
      for non-US markets.
    - ``start`` defaults to "2026-01-01" rather than "as far back as
      Stooq has" — a deliberately small, recent window so a first
      run (or a test) fetches quickly rather than pulling a decade of
      daily bars by accident. Pass ``start=None`` explicitly for
      Stooq's full available history, or any other date to set your
      own window. ``end`` defaults to ``None`` ("through Stooq's most
      recent close"). Dates may be given as "YYYY-MM-DD" or Stooq's
      own "YYYYMMDD"; both are normalized before the request.
"""

DEFAULT_START = "2026-01-01"

import re
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Sequence

import requests


class StockHistorySource:
    """
    Fetches full daily OHLCV history for a list of tickers from Stooq,
    once, and yields a single bulk dict covering all of them.

    Args:
        tickers:       Ticker symbols, e.g. ["AAPL", "MSFT"]. Bare US
                       tickers get ``.us`` appended automatically; for
                       other markets pass the full Stooq symbol (e.g.
                       "ntt.jp", "bp.uk"). Must be non-empty.
        start:         First date to include ("YYYY-MM-DD" or
                       "YYYYMMDD"). Defaults to "2026-01-01". Pass
                       ``start=None`` explicitly for "as far back as
                       Stooq has".
        end:           Last date to include (same formats). Omit for
                       "through Stooq's most recent close".
        request_pause: Seconds to sleep between per-ticker requests.
                       Default 0.25 — a light, polite pace, not a rate
                       limit Stooq is known to enforce.
        timeout:       Per-request HTTP timeout in seconds. Default 15
                       (longer than ``StocksSource``'s 10s, since a
                       multi-year CSV is a larger response).

    Example:
        >>> history = StockHistorySource(tickers=["AAPL", "MSFT"],
        ...                               start="2020-01-01")
        >>> source = Source(fn=history.run, name="price_history")
    """

    _HISTORY_URL = "https://stooq.com/q/d/l/"

    # Sentinel distinguishing "caller didn't pass start=" (use
    # DEFAULT_START) from "caller explicitly passed start=None"
    # (means "as far back as Stooq has" -- a real, different request).
    _UNSET = object()

    def __init__(
        self,
        tickers: Sequence[str],
        start: Optional[str] = _UNSET,
        end: Optional[str] = None,
        request_pause: float = 0.25,
        timeout: float = 15.0,
    ):
        if not tickers:
            raise ValueError(
                "StockHistorySource requires at least one ticker, got "
                f"{tickers!r}"
            )
        self.tickers = [self._normalize_ticker(t) for t in tickers]
        self.display_tickers = [self._display_ticker(t) for t in self.tickers]
        if start is self._UNSET:
            start = DEFAULT_START
        self.start = self._normalize_date(start)
        self.end = self._normalize_date(end)
        self.request_pause = request_pause
        self.timeout = timeout

    # ── Ticker / date normalization ─────────────────────────────────────

    @staticmethod
    def _normalize_ticker(ticker: str) -> str:
        """Append `.us` to bare US tickers; leave fully-qualified symbols alone."""
        t = ticker.strip().lower()
        if "." in t:
            return t
        return f"{t}.us"

    @staticmethod
    def _display_ticker(ticker: str) -> str:
        """Human-friendly ticker for message keys, e.g. 'aapl.us' -> 'AAPL'."""
        return ticker.split(".")[0].upper()

    @staticmethod
    def _normalize_date(date: Optional[str]) -> Optional[str]:
        """Accept 'YYYY-MM-DD' or 'YYYYMMDD'; return Stooq's 'YYYYMMDD' form."""
        if date is None:
            return None
        d = date.strip()
        if re.fullmatch(r"\d{8}", d):
            return d
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", d):
            return d.replace("-", "")
        raise ValueError(
            f"date must be 'YYYY-MM-DD' or 'YYYYMMDD', got {date!r}"
        )

    # ── HTTP + CSV parsing ───────────────────────────────────────────────

    def _fetch_one(self, ticker: str) -> List[Dict]:
        """Fetch and parse one ticker's full daily-bar CSV from Stooq."""
        params = {"s": ticker, "i": "d"}
        if self.start:
            params["d1"] = self.start
        if self.end:
            params["d2"] = self.end

        resp = requests.get(self._HISTORY_URL, params=params, timeout=self.timeout)
        resp.raise_for_status()

        lines = [ln.strip() for ln in resp.text.splitlines() if ln.strip()]
        if not lines:
            raise ValueError(f"Stooq returned an empty response for {ticker!r}.")

        # Stooq serves a plain-text error instead of CSV for an unknown
        # or de-listed symbol, e.g. "No data" -- treat anything that
        # isn't the expected header as "no data" rather than trying to
        # parse it as a row.
        header = lines[0].lower()
        if not header.startswith("date,open,high,low,close"):
            raise ValueError(
                f"Stooq returned no data for {ticker!r} "
                f"(response: {lines[0]!r})."
            )

        bars: List[Dict] = []
        for line in lines[1:]:
            fields = line.split(",")
            if len(fields) < 6:
                continue
            date, open_s, high_s, low_s, close_s, volume_s = fields[:6]

            def _to_float(s: str) -> Optional[float]:
                s = s.strip()
                if not s or s.upper() in {"N/D", "N/A"}:
                    return None
                try:
                    return float(s)
                except ValueError:
                    return None

            bars.append({
                "date":   date,
                "open":   _to_float(open_s),
                "high":   _to_float(high_s),
                "low":    _to_float(low_s),
                "close":  _to_float(close_s),
                "volume": _to_float(volume_s),
            })

        if not bars:
            raise ValueError(f"Stooq returned no rows for {ticker!r}.")

        return bars

    # ── Generator ─────────────────────────────────────────────────────────

    def run(self):
        """
        One-shot generator: fetch every ticker's history, then yield a
        single bulk dict and stop.

        Compatible with Source(fn=history.run, name="price_history")
        directly -- Source() in dsl/blocks/source.py auto-wraps
        generators. Mirrors starter_source.Starter's "fire once, then
        stop" shape rather than StocksSource's "poll forever" shape,
        since a backtest wants the full history exactly once.
        """
        history: Dict[str, List[Dict]] = {}
        errors: Dict[str, str] = {}

        for raw_ticker, display in zip(self.tickers, self.display_tickers):
            try:
                history[display] = self._fetch_one(raw_ticker)
            except Exception as exc:  # noqa: BLE001 -- one bad ticker shouldn't sink the rest
                errors[display] = str(exc)

            if self.request_pause > 0:
                time.sleep(self.request_pause)

        message = {
            "type":      "stock_history",
            "tickers":   self.display_tickers,
            "start":     self.start,
            "end":       self.end,
            "history":   history,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        if errors:
            message["errors"] = errors

        yield message
