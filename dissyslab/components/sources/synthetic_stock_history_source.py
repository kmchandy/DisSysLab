# dissyslab/components/sources/synthetic_stock_history_source.py

"""
SyntheticStockHistorySource: Generates fake-but-plausible daily OHLCV
price history for one or more tickers, with no network call at all.

Why this exists
================

``StockHistorySource`` (``stock_history_source.py``) wraps Stooq's
historical-data endpoint (``stooq.com/q/d/l/``). As of 2026-07-28 that
endpoint 404s -- including the exact URL Stooq's own site links to
(confirmed by hand: opening it directly in a browser and via three
separate ``requests.get`` variants all returned Stooq's own 404 page,
not a network error). Something changed or was discontinued on
Stooq's side; the fix (if there is one) needs more recon than "guess
a different URL shape."

Rather than block a whole backtest-office prototype on that unknown,
this class produces synthetic history in the *same message shape*
``StockHistorySource`` does, so every downstream agent (backtester,
portfolio-builder, robustness-selector, stats-and-ranking, ...) can be
built and exercised today. Swap this for ``StockHistorySource`` the
moment real data is reachable -- the message shape is identical, so
nothing downstream needs to change.

**This is not real market data. It is a per-ticker geometric random
walk** (independent daily log-returns, normally distributed) with no
real correlation structure, no real drift regime changes, no real
volatility clustering, and no connection whatsoever to any actual
company. It exists to unblock pipeline plumbing and testing, not to
produce a strategy ranking anyone should act on. Every message this
class emits is stamped ``"synthetic": True`` for exactly that reason
-- so it is never mistaken for real output further down a pipeline or
in a report.

Message shape (matches ``StockHistorySource`` plus one added key):
    {
        "type":      "stock_history",
        "synthetic": True,
        "tickers":   ["AAPL", "MSFT", ...],
        "start":     "20150101",
        "end":       "20260728",
        "history": {
            "AAPL": [{"date": "2015-01-02", "open": ..., "high": ...,
                      "low": ..., "close": ..., "volume": ...}, ...],
            "MSFT": [...],
        },
        "timestamp": "2026-07-28T21:34:56+00:00",
    }

Usage:
    from dissyslab.components.sources.synthetic_stock_history_source import (
        SyntheticStockHistorySource,
    )
    from dissyslab.blocks import Source

    fake_history = SyntheticStockHistorySource(
        tickers=["AAPL", "MSFT", "GOOGL"],
        start="2015-01-01",
        end="2025-01-01",
        seed=42,   # reproducible; omit for a different run each time
    )
    source = Source(fn=fake_history.run, name="price_history")

Design notes:
    - One-shot generator (yields once, then stops) -- same "send once"
      shape as ``StockHistorySource``, so a downstream JOIN/synchronizer
      pairing this with another single-message branch works unchanged.
    - Trading days = plain weekdays between ``start`` and ``end``
      inclusive. No holiday calendar -- a known, deliberate
      simplification; real backtests need a real calendar, synthetic
      prototyping doesn't.
    - ``seed`` makes the whole run reproducible: same seed, same
      tickers, same dates -> identical output every time. Each ticker
      still gets its own distinct path (derived from ``seed`` + the
      ticker name), not a copy of the first ticker's path. Leave
      ``seed=None`` for a fresh random run each time.
    - ``initial_price`` may be a single number (applied to every
      ticker) or a ``{ticker: price}`` dict for tickers that should
      start at different levels; unlisted tickers fall back to 100.0.
    - Daily bars use a simple, plausible-looking OHLC construction
      (open = previous close; high/low bracket open and close with a
      small extra random wiggle) -- good enough to exercise a
      backtester's plumbing, not a realistic intraday model.
"""

import hashlib
import math
import random
from datetime import date, datetime, timedelta, timezone
from typing import Dict, List, Optional, Sequence, Union


class SyntheticStockHistorySource:
    """
    Generates a per-ticker daily-bar random walk and yields it as a
    single bulk dict, in the same shape ``StockHistorySource`` uses.

    Args:
        tickers:           Ticker symbols, e.g. ["AAPL", "MSFT"]. Used
                            only as labels -- no real market is
                            queried. Must be non-empty.
        start:              First date to include ("YYYY-MM-DD" or
                            "YYYYMMDD"). Default "2015-01-01" -- a
                            decade-long window, since this class exists
                            to unblock multi-year backtests, unlike
                            ``StockHistorySource``'s short recent-data
                            default.
        end:                Last date to include (same formats).
                            Default: today (UTC).
        initial_price:      Starting price. A single number applied to
                            every ticker, or a ``{ticker: price}`` dict
                            for per-ticker starting levels. Default 100.0.
        annual_drift:       Expected annualized log-return. Default
                            0.08 (8%/year), a generic long-run equity
                            assumption -- not a forecast of anything.
        annual_volatility:  Annualized log-return volatility. Default
                            0.25 (25%/year), a generic single-stock
                            assumption.
        seed:               Optional int. Same seed + same tickers +
                            same dates -> identical output every run.
                            ``None`` (default) -> different each run.

    Example:
        >>> fake = SyntheticStockHistorySource(tickers=["AAPL", "MSFT"],
        ...                                     start="2020-01-01", seed=1)
        >>> source = Source(fn=fake.run, name="price_history")
    """

    def __init__(
        self,
        tickers: Sequence[str],
        start: Optional[str] = "2015-01-01",
        end: Optional[str] = None,
        initial_price: Union[float, Dict[str, float]] = 100.0,
        annual_drift: float = 0.08,
        annual_volatility: float = 0.25,
        seed: Optional[int] = None,
    ):
        if not tickers:
            raise ValueError(
                "SyntheticStockHistorySource requires at least one "
                f"ticker, got {tickers!r}"
            )
        self.tickers = list(tickers)
        self.display_tickers = [t.strip().upper() for t in tickers]

        start_date = self._parse_date(start) if start else date(2015, 1, 1)
        end_date = self._parse_date(end) if end else datetime.now(timezone.utc).date()
        if end_date < start_date:
            raise ValueError(
                f"end ({end_date.isoformat()}) is before start "
                f"({start_date.isoformat()})"
            )
        self._start_date = start_date
        self._end_date = end_date
        # Stored in Stooq's own YYYYMMDD form so a message from this
        # class and a message from StockHistorySource report `start`/
        # `end` identically.
        self.start = start_date.strftime("%Y%m%d")
        self.end = end_date.strftime("%Y%m%d")

        self.initial_price = initial_price
        self.annual_drift = annual_drift
        self.annual_volatility = annual_volatility
        self.seed = seed

    # ── Date parsing ─────────────────────────────────────────────────────

    @staticmethod
    def _parse_date(d: str) -> date:
        s = d.strip()
        if len(s) == 8 and s.isdigit():
            return datetime.strptime(s, "%Y%m%d").date()
        return datetime.strptime(s, "%Y-%m-%d").date()

    def _trading_days(self) -> List[date]:
        """Plain weekdays (Mon-Fri) between start and end, inclusive.

        No holiday calendar -- see module docstring's Design notes.
        """
        days = []
        d = self._start_date
        one_day = timedelta(days=1)
        while d <= self._end_date:
            if d.weekday() < 5:  # Mon=0 .. Sun=6
                days.append(d)
            d += one_day
        return days

    # ── Per-ticker price path ────────────────────────────────────────────

    def _initial_price_for(self, ticker: str) -> float:
        if isinstance(self.initial_price, dict):
            return float(self.initial_price.get(ticker, 100.0))
        return float(self.initial_price)

    def _rng_for(self, ticker: str) -> random.Random:
        """A distinct-but-reproducible RNG per ticker.

        Two tickers must not walk the same path even with the same
        `seed`, or a multi-ticker synthetic run would be trivially
        degenerate (every column identical). Deriving a per-ticker
        seed from (seed, ticker) keeps both properties: reproducible
        across runs, distinct across tickers.

        Caught the hard way: an earlier version passed the tuple
        ``(self.seed, ticker)`` straight to ``random.Random()``. That
        works on Python <= 3.10, where ``random.seed()`` accepts any
        hashable object, but raises ``TypeError`` on 3.11+, where only
        None/int/float/str/bytes/bytearray are accepted -- caught when
        a user ran this on Python 3.12, not by this module's own tests
        (which happened to run under 3.10). Using Python's builtin
        ``hash()`` here instead would "fix" the TypeError but silently
        break reproducibility across separate process runs: str
        hashing is randomized per-process (``PYTHONHASHSEED``) unless
        explicitly disabled, so the same ``seed`` would produce a
        different path each run -- exactly the property this method
        exists to guarantee. ``hashlib`` is unaffected by that
        randomization, so it's what actually gives a stable, portable
        per-ticker seed.
        """
        if self.seed is None:
            return random.Random()
        key = f"{self.seed!r}:{ticker}".encode("utf-8")
        digest = hashlib.sha256(key).digest()
        seed_int = int.from_bytes(digest[:8], "big")
        return random.Random(seed_int)

    def _generate_bars(self, ticker: str, days: List[date]) -> List[Dict]:
        rng = self._rng_for(ticker)
        price = self._initial_price_for(ticker)
        mu = self.annual_drift / 252.0
        sigma = self.annual_volatility / math.sqrt(252.0)

        bars: List[Dict] = []
        for d in days:
            open_ = price
            daily_return = rng.gauss(mu, sigma)
            close = open_ * math.exp(daily_return)
            wiggle_hi = abs(rng.gauss(0.0, sigma / 2.0))
            wiggle_lo = abs(rng.gauss(0.0, sigma / 2.0))
            high = max(open_, close) * (1.0 + wiggle_hi)
            low = min(open_, close) * (1.0 - wiggle_lo)
            volume = int(rng.uniform(1_000_000, 50_000_000))

            bars.append({
                "date":   d.isoformat(),
                "open":   round(open_, 2),
                "high":   round(high, 2),
                "low":    round(max(low, 0.01), 2),
                "close":  round(close, 2),
                "volume": volume,
            })
            price = close

        return bars

    # ── Generator ─────────────────────────────────────────────────────────

    def run(self):
        """
        One-shot generator: build every ticker's synthetic history,
        then yield a single bulk dict and stop -- same "fire once"
        shape as ``StockHistorySource.run()`` and ``starter_source``.
        """
        days = self._trading_days()
        history = {
            display: self._generate_bars(raw, days)
            for raw, display in zip(self.tickers, self.display_tickers)
        }

        yield {
            "type":      "stock_history",
            "synthetic": True,
            "tickers":   self.display_tickers,
            "start":     self.start,
            "end":       self.end,
            "history":   history,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
