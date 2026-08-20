# dissyslab/components/sources/stocks_source.py

"""
StocksSource — one price reading per poll, from Yahoo Finance via yfinance.

Why yfinance, and why you fetch your own data
---------------------------------------------

This source used to read Stooq's free CSV quote endpoint. That endpoint
was removed — every request returns 404, for every ticker spelling — and
Stooq's daily-history endpoint now answers with a JavaScript
proof-of-work browser challenge rather than data. Both were free, both
needed no key, and both broke inside two months. Nothing in the framework
noticed, because this source caught each failure and reported it as a
``stocks_error`` message that no sink recognised. See
``archive/ISSUES_walkthrough_2026-08-17.md``, C1 to C3.

``yfinance`` replaces it, and brings one constraint worth stating plainly
here rather than leaving to be discovered:

**Every user fetches their own data. We ship none of it.** Yahoo's terms
do not permit redistributing their market data, so this repository
contains no prices, no cached quotes, and no sample market CSVs. The
backtesting offices already work this way — ``mac_speed_suite`` ships a
``download_stock_history_from_yf.py`` that each user runs once to build
their own local copy. That is not an inconvenience to route around; it is
the condition on which the data is available at all.

**yfinance is an optional dependency.** ``pip install dissyslab`` does not
install it, because the offices a first-year runs first need no market
data. Offices that do need it say so::

    pip install "dissyslab[market]"

The import is deferred to the first fetch so that ``SOURCE_REGISTRY`` —
and therefore ``dsl check``, ``dsl list``, and every non-market office —
keeps working on a machine that has never installed yfinance. A student
who wires up ``stocks`` without the extra gets one clear sentence naming
the command to run, not an ImportError at module load.

**Yahoo's endpoints are unofficial.** yfinance is a community wrapper
around them: maintained, widely used, and still not an API with a
contract. Expect it to need an occasional upgrade. That is better than
what it replaces, where the break was ours to diagnose from scratch.

Message shape
-------------

Unchanged from the Stooq version, so no sink or downstream agent had to
change::

    {"type": "stocks", "ticker": "AAPL", "market": "NMS",
     "price": 305.59, "open": 306.21, "high": 307.66, "low": 302.94,
     "previous_close": 305.77, "change": -0.18, "change_pct": -0.059,
     "currency": "USD", "market_date": "2026-08-18",
     "market_time": "03:41:02", "timestamp": "2026-08-18T03:41:02+00:00"}

Two deliberate changes. ``previous_close`` is new. And ``change`` /
``change_pct`` are now measured against the previous close rather than
against the session open — "up 2% today" means since yesterday's close in
every other context a student will meet, and reading against the open
silently meant something else.

A failed fetch yields ``{"type": "stocks_error", ...}`` and keeps polling,
so one bad request does not end the office. Since 1.7.2 the run summary
counts those: a source whose output is *all* errors fails the run loudly
instead of producing an empty brief that reports success.
"""

from datetime import datetime, timezone
import time
from typing import Any, Optional


class StocksSource:
    """
    Polls Yahoo Finance for a ticker's latest price, yielding one dict
    per reading.

    Args:
        ticker:        Symbol as Yahoo spells it — ``"AAPL"``, ``"BP.L"``,
                       ``"7203.T"``. A trailing ``.us`` (the Stooq
                       convention this source used to require) is
                       stripped, so old ``office.md`` files keep working.
        poll_interval: Seconds between readings. Default 300 (5 min).
                       Yahoo is not a subscription feed; polling it hard
                       earns a rate limit, and no brief needs tick data.
        max_readings:  Stop after this many. ``None`` runs forever. Keep a
                       small value in gallery offices, so a student trying
                       something out gets an office that ends.
        session:       Optional ``requests.Session``. Not settable from
                       ``office.md``, which takes Python literals only —
                       this is for tests, and for users behind a proxy
                       that rejects yfinance's default HTTP client.

    Example:
        >>> stocks = StocksSource(ticker="AAPL", max_readings=1)
        >>> source = Source(fn=stocks.run, name="stocks")
    """

    def __init__(
        self,
        ticker: str = "AAPL",
        poll_interval: int = 300,
        max_readings: Optional[int] = None,
        session: Any = None,
    ):
        self.ticker = self._normalize_ticker(ticker)
        self.poll_interval = poll_interval
        self.max_readings = max_readings
        self.session = session

    @staticmethod
    def _normalize_ticker(ticker: str) -> str:
        """Yahoo spells US tickers bare. Strip the Stooq-era ``.us``.

        Kept rather than dropped: ``stocks(ticker="aapl.us")`` appeared in
        this repository's own examples for months, and a student who
        copied one should get a price, not a confusing "no data". Other
        suffixes (``.L``, ``.T``) are Yahoo's own market codes and are
        preserved untouched.
        """
        t = ticker.strip()
        if t.lower().endswith(".us"):
            t = t[: -len(".us")]
        return t.upper() if "." not in t else t

    def _yf(self):
        """Import yfinance, or explain how to get it.

        Deferred on purpose. The registry imports this module to resolve
        the name ``stocks``, so a top-level ``import yfinance`` would
        break ``dsl check`` for every office in the gallery, market or
        not, on any machine without the extra.
        """
        try:
            import yfinance  # noqa: WPS433 — deliberately deferred
        except ImportError as exc:
            raise ImportError(
                "The 'stocks' source needs yfinance, which is not "
                "installed.\n"
                '  Fix: pip install "dissyslab[market]"\n'
                "       (or: pip install yfinance)\n"
                "yfinance is optional on purpose -- the offices you run "
                "first need no market data, and Yahoo's terms mean each "
                "user fetches their own."
            ) from exc
        return yfinance

    # ── Fetch ─────────────────────────────────────────────────────────────

    def _fetch(self) -> dict:
        """Fetch one price reading. Raises on anything unusable."""
        yf = self._yf()
        kwargs = {"session": self.session} if self.session is not None else {}
        info = yf.Ticker(self.ticker, **kwargs).fast_info

        def _number(attr: str) -> Optional[float]:
            """``fast_info`` raises rather than returning ``None`` for
            several fields when Yahoo has no data for a symbol. Every
            such signal means the same thing here: absent."""
            try:
                value = getattr(info, attr)
            except Exception:  # noqa: BLE001 — absence, however signalled
                return None
            return float(value) if isinstance(value, (int, float)) else None

        def _text(attr: str, default: str = "") -> str:
            try:
                value = getattr(info, attr)
            except Exception:  # noqa: BLE001
                return default
            return str(value) if value else default

        price = _number("last_price")
        if price is None:
            raise ValueError(
                f"Yahoo returned no price for {self.ticker!r}. Check the "
                f"symbol as Yahoo spells it (AAPL, BP.L, 7203.T) -- a "
                f"symbol that does not exist looks exactly like this."
            )

        previous_close = _number("previous_close")
        change = change_pct = None
        if previous_close:
            change = round(price - previous_close, 4)
            change_pct = round(
                (price - previous_close) / previous_close * 100, 3
            )

        now = datetime.now(timezone.utc)
        return {
            "type": "stocks",
            "ticker": self.ticker,
            "market": _text("exchange"),
            "price": round(price, 4),
            "open": _number("open"),
            "high": _number("day_high"),
            "low": _number("day_low"),
            "previous_close": previous_close,
            "change": change,
            "change_pct": change_pct,
            "currency": _text("currency", "USD"),
            "market_date": now.strftime("%Y-%m-%d"),
            "market_time": now.strftime("%H:%M:%S"),
            "timestamp": now.isoformat(),
        }

    # ── Generator ─────────────────────────────────────────────────────────

    def run(self):
        """
        Yield one price dict per poll.

        Compatible with ``Source(fn=stocks.run, name="stocks")`` --
        ``Source`` auto-wraps generators.
        """
        readings = 0

        while True:
            try:
                yield self._fetch()
            except Exception as exc:  # noqa: BLE001 — surface, do not crash
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
