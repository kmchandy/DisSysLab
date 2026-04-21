# dissyslab/components/sources/stocks_source.py

"""
StocksSource: Emits current stock-price dicts into a DisSysLab pipeline.

StocksSource polls Stooq (https://stooq.com/), a free financial data
service that returns quotes as CSV over plain HTTP. No API key is
required, there are no signups, and it works from home networks,
school networks, and cloud IPs alike.

Each message looks like:
    {
        "type":         "stocks",
        "ticker":       "AAPL",
        "market":       "US",
        "price":        187.42,      # most recent trade
        "open":         185.10,      # today's open
        "high":         188.30,      # today's high so far
        "low":          184.90,      # today's low so far
        "change":       2.32,        # price - open
        "change_pct":   1.253,       # (price - open) / open * 100
        "currency":     "USD",
        "market_date":  "2026-04-21",
        "market_time":  "15:30:45",
        "timestamp":    "2026-04-21T21:34:56+00:00",
    }

Usage:
    from dissyslab.components.sources.stocks_source import StocksSource
    from dissyslab.blocks import Source

    stocks = StocksSource(ticker="AAPL", poll_interval=300)
    source = Source(fn=stocks.run, name="stocks")

For testing (fire immediately, stop after one reading):
    stocks = StocksSource(ticker="AAPL", poll_interval=0, max_readings=1)

Design notes:
    - First reading fires *immediately* when `run()` is first called, so
      a newly started office produces a briefing in the first few seconds
      instead of making the student wait a full poll interval.
    - If the network request fails (offline, unknown ticker), the source
      yields an error dict instead of crashing. The pipeline stays alive.
    - `change` and `change_pct` are relative to today's open, not the
      previous day's close. This is a single-request metric — faithful
      to the intraday direction of the stock without the second HTTP call
      that a "vs previous close" metric would require.
    - Stooq uses `.us` suffix for US tickers (e.g. aapl.us, googl.us).
      This class adds the suffix automatically when the user passes a
      bare ticker. For non-US markets, pass the full Stooq symbol
      (e.g. ticker="ntt.jp" for Japan, ticker="bp.uk" for the UK).
"""

import time
from datetime import datetime, timezone
from typing import Optional

import requests


class StocksSource:
    """
    Polls Stooq for a ticker's latest price and yields one dict per reading.

    Args:
        ticker:        Ticker symbol. Bare US tickers like "AAPL" work —
                       `.us` is appended automatically. For other markets,
                       pass the full Stooq symbol (e.g. "ntt.jp", "bp.uk").
        poll_interval: Seconds between readings. Default: 300 (5 min).
        max_readings:  Stop after this many readings. None = run forever.
                       Set to a small number for testing.

    Example:
        >>> stocks = StocksSource(ticker="AAPL", poll_interval=300)
        >>> source = Source(fn=stocks.run, name="stocks")
    """

    _QUOTE_URL = "https://stooq.com/q/l/"

    def __init__(
        self,
        ticker: str = "AAPL",
        poll_interval: int = 300,
        max_readings: Optional[int] = None,
    ):
        self.ticker = self._normalize_ticker(ticker)
        self.poll_interval = poll_interval
        self.max_readings = max_readings

    @staticmethod
    def _normalize_ticker(ticker: str) -> str:
        """Append `.us` to bare US tickers; leave fully-qualified symbols alone."""
        t = ticker.strip().lower()
        if "." in t:
            return t
        return f"{t}.us"

    def _market_code(self) -> str:
        """Return the market suffix in uppercase ('US', 'JP', 'UK', ...)."""
        _, _, suffix = self.ticker.partition(".")
        return suffix.upper() or "US"

    @staticmethod
    def _guess_currency(market: str) -> str:
        return {
            "US": "USD",
            "UK": "GBP",
            "DE": "EUR",
            "FR": "EUR",
            "JP": "JPY",
            "HK": "HKD",
            "CA": "CAD",
        }.get(market, "")

    # ── HTTP helper ───────────────────────────────────────────────────────

    def _fetch(self) -> dict:
        """Fetch one price reading from Stooq and parse the CSV."""
        resp = requests.get(
            self._QUOTE_URL,
            params={
                "s": self.ticker,
                "f": "sd2t2ohlc",   # symbol, date, time, open, high, low, close
                "h": "",            # include header row
                "e": "csv",         # CSV format
            },
            timeout=10,
        )
        resp.raise_for_status()

        lines = [ln.strip() for ln in resp.text.splitlines() if ln.strip()]
        if len(lines) < 2:
            raise ValueError(f"Stooq returned no data for '{self.ticker}'.")

        # Expected header: Symbol,Date,Time,Open,High,Low,Close
        fields = lines[1].split(",")
        if len(fields) < 7:
            raise ValueError(f"Unexpected Stooq row for '{self.ticker}': {lines[1]!r}")

        symbol, date, stime, open_s, high_s, low_s, close_s = fields[:7]

        def _to_float(s: str) -> Optional[float]:
            s = s.strip()
            if not s or s.upper() in {"N/D", "N/A"}:
                return None
            try:
                return float(s)
            except ValueError:
                return None

        price = _to_float(close_s)
        open_ = _to_float(open_s)
        high = _to_float(high_s)
        low = _to_float(low_s)

        if price is None:
            raise ValueError(
                f"Stooq returned no price for '{self.ticker}'. "
                "The ticker may not exist or the market may be closed."
            )

        change = None
        change_pct = None
        if open_ is not None and open_ != 0 and price is not None:
            change = round(price - open_, 4)
            change_pct = round((price - open_) / open_ * 100, 3)

        market = self._market_code()
        return {
            "type": "stocks",
            "ticker": self.ticker.split(".")[0].upper(),
            "market": market,
            "price": price,
            "open": open_,
            "high": high,
            "low": low,
            "change": change,
            "change_pct": change_pct,
            "currency": self._guess_currency(market),
            "market_date": date,
            "market_time": stime,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    # ── Generator ─────────────────────────────────────────────────────────

    def run(self):
        """
        Generator that yields one price dict per poll.

        Compatible with Source(fn=stocks.run, name="stocks") directly —
        Source() in dsl/blocks/source.py auto-wraps generators.
        """
        readings = 0

        while True:
            try:
                yield self._fetch()
            except Exception as exc:  # noqa: BLE001 — surface any failure cleanly
                yield {
                    "type": "stocks_error",
                    "ticker": self.ticker,
                    "error": str(exc),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }

            readings += 1
            if self.max_readings is not None and readings >= self.max_readings:
                return

            if self.poll_interval > 0:
                time.sleep(self.poll_interval)
