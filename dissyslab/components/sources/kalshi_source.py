"""
KalshiSource — Kalshi Trade API v2: explicit tickers **or** keyword/series discovery.

**Ticker mode** (unchanged): poll ``GET /markets/{ticker}`` for each ticker.

**Discovery mode** (streaming-style poll): match a **keyword** against **open
events** (``GET /events`` — titles, subtitles, categories) *and* **open markets**
(``GET /markets`` — rules, strike text). Kalshi's default market listing is
dominated by sports; geopolitics and commodity questions show up reliably on
**events**, so keyword discovery unions both feeds before expanding each
``event_ticker``.

Public read endpoints — no API key required for typical market data.

Example ``office.md``::

    # All open contracts in a series (e.g. WTI), one message per event per poll
    Sources: kalshi(series_ticker=\"KXWTI\", poll_interval=60)

    # Keyword scan (substring, case-insensitive) across paginated open markets
    Sources: kalshi(keyword=\"oil\", poll_interval=90, max_scan_markets=4000)

    # Original single-ticker poll
    Sources: kalshi(ticker=\"KXMYMARKET-24DEC01-T1234\", poll_interval=60)
"""

from __future__ import annotations

import re
import time
from datetime import datetime, timezone
from typing import Any, Callable, Optional
from urllib.parse import quote, urlencode

import requests


def _d(val: Any) -> Optional[float]:
    if val is None or val == "":
        return None
    try:
        return float(str(val).strip())
    except (TypeError, ValueError):
        return None


def _pct(x: Optional[float]) -> str:
    if x is None:
        return "n/a"
    return f"{x * 100:.1f}%"


def _roi_yes_if_win(ask: Optional[float]) -> str:
    """Percent return on premium if YES resolves in your favor (buy at ask)."""
    if ask is None or ask <= 0:
        return "n/a"
    return f"+{(1.0 - ask) / ask * 100:.0f}%"


def _roi_no_if_win(no_ask: Optional[float]) -> str:
    if no_ask is None or no_ask <= 0:
        return "n/a"
    return f"+{(1.0 - no_ask) / no_ask * 100:.0f}%"


def _market_text_blob(m: dict[str, Any]) -> str:
    parts = [
        m.get("title"),
        m.get("yes_sub_title"),
        m.get("no_sub_title"),
        m.get("rules_primary"),
        m.get("event_ticker"),
        m.get("ticker"),
    ]
    return " ".join(str(p or "") for p in parts)


def _event_text_blob(ev: dict[str, Any]) -> str:
    """Fields on ``GET /events`` rows used for keyword discovery."""
    parts = [
        ev.get("title"),
        ev.get("sub_title"),
        ev.get("category"),
        ev.get("series_ticker"),
        ev.get("event_ticker"),
    ]
    return " ".join(str(p or "") for p in parts)


def _outcome_label(m: dict[str, Any]) -> str:
    return (
        (m.get("yes_sub_title") or "").strip()
        or (m.get("title") or "").strip()
        or (m.get("ticker") or "").strip()
    )


def _format_outcome_block(m: dict[str, Any]) -> str:
    """One outcome as a spaced, nested bullet block (readable in console / UI)."""
    last_y = _d(m.get("last_price_dollars"))
    yb, ya = _d(m.get("yes_bid_dollars")), _d(m.get("yes_ask_dollars"))
    mid = None
    if yb is not None and ya is not None:
        mid = (yb + ya) / 2.0
    last_n = (1.0 - last_y) if last_y is not None else None
    na = _d(m.get("no_ask_dollars"))
    label = _outcome_label(m)
    lines = [
        f"  • {label[:200]}",
        f"      · YES last     {_pct(last_y)}",
        f"      · YES mid      {_pct(mid)}",
        f"      · Buy YES @ ask → if wins  {_roi_yes_if_win(ya)}",
        f"      · NO implied   {_pct(last_n)}",
        f"      · Buy NO @ ask → if wins  {_roi_no_if_win(na)}",
    ]
    return "\n".join(lines)


class KalshiSource:
    """
    Poll Kalshi markets: either fixed tickers or discovery by ``keyword`` /
    ``series_ticker``.

    Discovery groups by ``event_ticker`` and emits one composite message per
    event (all sibling outcomes with prices).

    Args:
        ticker:          Single market ticker (ticker mode).
        tickers:         Comma-separated tickers (ticker mode).
        keyword:         Substring match while scanning **open events** and **open markets**
                         (discovery; see ``max_scan_events``).
        series_ticker:   Only scan markets in this Kalshi series (discovery).
        match_whole_word: If True, ``keyword`` must match as a whole word.
        page_size:       Page size for ``GET /markets`` / ``GET /events``.
        max_scan_markets: Cap for paginated ``GET /markets`` scan.
        max_scan_events: Cap for paginated ``GET /events`` scan (keyword mode).
            Kalshi's default market feed is sports-heavy; matching on **events**
            (titles, categories) finds geopolitics and macro series that rarely
            appear in the first pages of ``/markets``.
        poll_interval:   Seconds between full polling rounds.
        page_delay_seconds: Sleep after each **paginated** HTTP page (events /
            markets list) before the next page — reduces 429 rate limits.
        event_expand_delay_seconds: Sleep before each **additional** event
            expansion (``GET /markets?event_ticker=``) after the first.
        max_http_retries: Retries for a single HTTP call on 429 / 503 before
            surfacing an error.
        backoff_cap_seconds: Max sleep between retries (still honors
            ``Retry-After`` when lower).
        base_url:        API root including ``/trade-api/v2``.
        max_readings:    Stop after this many rounds (``None`` = forever).

    Ticker mode is used when ``ticker`` or ``tickers`` is set **and** neither
    ``keyword`` nor ``series_ticker`` is set. If ``keyword`` or ``series_ticker``
    is set, discovery mode is used (explicit tickers are ignored).
    """

    _UA = "DisSysLab/1.0 KalshiSource (+https://github.com/kmchandy/DisSysLab)"

    def __init__(
        self,
        ticker: Optional[str] = None,
        tickers: Optional[str] = None,
        keyword: Optional[str] = None,
        series_ticker: Optional[str] = None,
        match_whole_word: bool = False,
        page_size: int = 200,
        max_scan_markets: int = 4000,
        max_scan_events: int = 8000,
        poll_interval: int = 60,
        page_delay_seconds: float = 0.2,
        event_expand_delay_seconds: float = 0.15,
        max_http_retries: int = 10,
        backoff_cap_seconds: float = 90.0,
        base_url: str = "https://external-api.kalshi.com/trade-api/v2",
        max_readings: Optional[int] = None,
    ):
        self.poll_interval = int(poll_interval)
        self.base_url = base_url.rstrip("/")
        self.max_readings = max_readings
        self.page_size = max(1, min(int(page_size), 1000))
        self.max_scan_markets = max(1, int(max_scan_markets))
        self.max_scan_events = max(0, int(max_scan_events))
        self.page_delay_seconds = max(0.0, float(page_delay_seconds))
        self.event_expand_delay_seconds = max(0.0, float(event_expand_delay_seconds))
        self.max_http_retries = max(1, int(max_http_retries))
        self.backoff_cap_seconds = max(1.0, float(backoff_cap_seconds))
        self.keyword = (keyword or "").strip()
        self.series_ticker = (series_ticker or "").strip()
        self.match_whole_word = bool(match_whole_word)

        names: list[str] = []
        if tickers:
            names.extend(
                p.strip() for p in str(tickers).split(",") if p.strip()
            )
        if ticker and str(ticker).strip():
            names.append(str(ticker).strip())
        seen: set[str] = set()
        self._tickers: list[str] = []
        for n in names:
            if n not in seen:
                seen.add(n)
                self._tickers.append(n)

        self._discovery = bool(self.keyword or self.series_ticker)
        if self._discovery and self._tickers:
            raise ValueError(
                "KalshiSource: use either discovery (keyword / series_ticker) "
                "or explicit ticker / tickers, not both."
            )

        if not self._discovery and not self._tickers:
            raise ValueError(
                "KalshiSource needs ticker=, tickers=, keyword=, and/or "
                "series_ticker=.\n"
                "Examples:\n"
                '  kalshi(ticker="KXFOO-24DEC01")\n'
                '  kalshi(keyword="oil")\n'
                '  kalshi(series_ticker="KXWTI")\n'
                "Find tickers and series on https://kalshi.com or GET /markets."
            )

        self._matcher: Optional[Callable[[str], bool]]
        if self.keyword:
            if self.match_whole_word:
                pat = re.compile(r"\b" + re.escape(self.keyword) + r"\b", re.I)

                def _m(blob: str) -> bool:
                    return bool(pat.search(blob))

                self._matcher = _m
            else:

                def _m2(blob: str) -> bool:
                    return self.keyword.lower() in blob.lower()

                self._matcher = _m2
        else:
            self._matcher = None

    def _sleep_pace(self) -> None:
        if self.page_delay_seconds > 0:
            time.sleep(self.page_delay_seconds)

    def _retry_after_seconds(self, resp: requests.Response, attempt: int) -> float:
        ra = resp.headers.get("Retry-After")
        if ra:
            try:
                return min(float(ra), self.backoff_cap_seconds)
            except (TypeError, ValueError):
                pass
        base = 0.5 * (2 ** (attempt - 1))
        return min(base, self.backoff_cap_seconds)

    def _get(
        self,
        path: str,
        params: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        q = f"?{urlencode(params)}" if params else ""
        url = f"{self.base_url}{path}{q}"
        attempt = 0
        while True:
            resp = requests.get(
                url,
                headers={"Accept": "application/json", "User-Agent": self._UA},
                timeout=30,
            )
            if resp.status_code in (429, 503):
                attempt += 1
                if attempt > self.max_http_retries:
                    resp.raise_for_status()
                wait = self._retry_after_seconds(resp, attempt)
                wait = max(0.1, wait)
                print(
                    f"[kalshi] HTTP {resp.status_code}; "
                    f"backing off {wait:.1f}s ({attempt}/{self.max_http_retries})…"
                )
                time.sleep(wait)
                continue
            resp.raise_for_status()
            return resp.json()

    def _fetch_market(self, ticker: str) -> dict[str, Any]:
        enc = quote(ticker, safe="")
        data = self._get(f"/markets/{enc}")
        m = data.get("market")
        if not isinstance(m, dict):
            raise ValueError(f"Unexpected response shape for {ticker!r}")
        return m

    def _iter_market_pages(
        self,
        extra: Optional[dict[str, Any]] = None,
    ) -> Any:
        """Yield market dicts until cursor exhausted or max_scan_markets hit."""
        scanned = 0
        cursor: Optional[str] = None
        while scanned < self.max_scan_markets:
            params: dict[str, Any] = {
                "status": "open",
                "limit": str(self.page_size),
            }
            if self.series_ticker:
                params["series_ticker"] = self.series_ticker
            if extra:
                params.update(extra)
            if cursor:
                params["cursor"] = cursor
            data = self._get("/markets", params)
            batch = data.get("markets") or []
            if not isinstance(batch, list):
                break
            for m in batch:
                if not isinstance(m, dict):
                    continue
                scanned += 1
                yield m
                if scanned >= self.max_scan_markets:
                    return
            cursor = data.get("cursor")
            if not cursor:
                break
            self._sleep_pace()

    def _iter_event_pages(self) -> Any:
        """Yield event dicts from ``GET /events`` (open) until cap or cursor end."""
        scanned = 0
        cursor: Optional[str] = None
        while scanned < self.max_scan_events:
            params: dict[str, Any] = {
                "status": "open",
                "limit": str(self.page_size),
            }
            if cursor:
                params["cursor"] = cursor
            data = self._get("/events", params)
            batch = data.get("events") or []
            if not isinstance(batch, list):
                break
            for ev in batch:
                if not isinstance(ev, dict):
                    continue
                scanned += 1
                yield ev
                if scanned >= self.max_scan_events:
                    return
            cursor = data.get("cursor")
            if not cursor:
                break
            self._sleep_pace()

    def _event_matches_series(self, ev: dict[str, Any]) -> bool:
        if not self.series_ticker:
            return True
        return ev.get("series_ticker") == self.series_ticker

    def _collect_event_tickers(self) -> list[str]:
        """
        Resolve event_tickers to expand.

        - With **keyword**: scan **open events** (titles, categories, …) *and*
          paginated **open markets** (rules text, strike titles). Union results.
          This avoids relying only on the sports-heavy default ``/markets`` feed.
        - **series_ticker** only (no keyword): scan markets in that series.
        """
        found: set[str] = set()

        if self.keyword and self._matcher is not None:
            for ev in self._iter_event_pages():
                if not self._event_matches_series(ev):
                    continue
                blob = _event_text_blob(ev)
                if not self._matcher(blob):
                    continue
                et = ev.get("event_ticker")
                if isinstance(et, str) and et:
                    found.add(et)

        if self.keyword or self.series_ticker:
            for m in self._iter_market_pages():
                et = m.get("event_ticker")
                if not et or not isinstance(et, str):
                    continue
                blob = _market_text_blob(m)
                if self._matcher is not None and not self._matcher(blob):
                    continue
                found.add(et)

        return sorted(found)

    def _markets_for_event(self, event_ticker: str) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        cursor: Optional[str] = None
        while True:
            params: dict[str, Any] = {
                "event_ticker": event_ticker,
                "status": "open",
                "limit": str(self.page_size),
            }
            if cursor:
                params["cursor"] = cursor
            data = self._get("/markets", params)
            batch = data.get("markets") or []
            if not isinstance(batch, list):
                break
            for m in batch:
                if isinstance(m, dict):
                    out.append(m)
            cursor = data.get("cursor")
            if not cursor:
                break
            self._sleep_pace()
        # Stable order: by YES ask / subtitle
        out.sort(key=lambda x: (_outcome_label(x), x.get("ticker", "")))
        return out

    @staticmethod
    def _to_message_single(m: dict[str, Any]) -> dict[str, str]:
        ticker = m.get("ticker", "")
        ytitle = (m.get("yes_sub_title") or "").strip()
        title = f"{ticker}" if not ytitle else f"{ticker} — {ytitle[:80]}"
        parts = [
            f"status={m.get('status', '')}",
            f"YES bid {m.get('yes_bid_dollars', '')} ask {m.get('yes_ask_dollars', '')}",
            f"NO bid {m.get('no_bid_dollars', '')} ask {m.get('no_ask_dollars', '')}",
            f"last {m.get('last_price_dollars', '')}",
            f"24h vol {m.get('volume_24h_fp', '')}",
        ]
        text = "\n".join(f"  • {p}" for p in parts)
        ts = m.get("updated_time") or m.get("open_time") or ""
        return {
            "source":    "kalshi",
            "title":     title[:200],
            "text":      text,
            "url":       "https://kalshi.com/",
            "timestamp": str(ts),
        }

    def _to_message_event(
        self,
        event_ticker: str,
        markets: list[dict[str, Any]],
    ) -> dict[str, str]:
        if not markets:
            return {
                "source":    "kalshi",
                "title":     f"{event_ticker} (no open markets)",
                "text":      "",
                "url":       "https://kalshi.com/",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        m0 = markets[0]
        ev_title = (m0.get("title") or "").strip() or event_ticker
        header = "\n".join(
            [
                "Event",
                f"  • {ev_title}",
                "",
                "Details",
                f"  • event_ticker : {event_ticker}",
                f"  • open markets : {len(markets)}",
                "",
                "How to read",
                "  • Each outcome below is one binary contract.",
                "  • “YES last” = last traded implied YES.",
                "  • “Buy … @ ask → if wins” = % gain on premium if that side pays $1.",
                "",
                "Outcomes",
                "",
            ]
        )
        blocks = [_format_outcome_block(m) for m in markets]
        body = "\n\n".join(blocks)
        text = header + body
        ts = max(
            (str(m.get("updated_time") or m.get("open_time") or "") for m in markets),
            default="",
        )
        title = f"{event_ticker} — {ev_title[:120]}"
        return {
            "source":    "kalshi",
            "title":     title[:200],
            "text":      text,
            "url":       "https://kalshi.com/",
            "timestamp": ts or datetime.now(timezone.utc).isoformat(),
        }

    def run(self):
        readings = 0
        while True:
            if self._discovery:
                try:
                    events = self._collect_event_tickers()
                    if not events:
                        yield {
                            "source":    "kalshi",
                            "title":     "Kalshi discovery — no matching events",
                            "text":      "\n".join(
                                [
                                    "No open events matched this poll.",
                                    "",
                                    "Search",
                                    f"  • keyword         : {self.keyword!r}",
                                    f"  • series_ticker   : {self.series_ticker!r}",
                                    "",
                                    "Limits",
                                    f"  • max_scan_markets : {self.max_scan_markets}",
                                    f"  • max_scan_events  : {self.max_scan_events}",
                                    "",
                                    "Try",
                                    "  • another keyword or series_ticker (e.g. KXWTI for WTI oil)",
                                    "  • raising max_scan_events / max_scan_markets",
                                ]
                            ),
                            "url":       "https://kalshi.com/",
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        }
                    for i, et in enumerate(events):
                        try:
                            if (
                                i > 0
                                and self.event_expand_delay_seconds > 0
                            ):
                                time.sleep(self.event_expand_delay_seconds)
                            mkts = self._markets_for_event(et)
                            yield self._to_message_event(et, mkts)
                        except Exception as exc:  # noqa: BLE001
                            yield {
                                "source":    "kalshi",
                                "title":     f"Kalshi error — event {et}",
                                "text":      str(exc),
                                "url":       "https://docs.kalshi.com/",
                                "timestamp": datetime.now(timezone.utc).isoformat(),
                            }
                except Exception as exc:  # noqa: BLE001
                    yield {
                        "source":    "kalshi",
                        "title":     "Kalshi discovery error",
                        "text":      str(exc),
                        "url":       "https://docs.kalshi.com/",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
            else:
                for t in self._tickers:
                    try:
                        m = self._fetch_market(t)
                        yield self._to_message_single(m)
                    except Exception as exc:  # noqa: BLE001
                        yield {
                            "source":    "kalshi",
                            "title":     f"Kalshi error — {t}",
                            "text":      str(exc),
                            "url":       "https://docs.kalshi.com/",
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        }

            readings += 1
            if self.max_readings is not None and readings >= self.max_readings:
                return

            if self.poll_interval > 0:
                mode = "discovery" if self._discovery else f"{len(self._tickers)} ticker(s)"
                print(
                    f"[kalshi] Polled ({mode}); sleeping {self.poll_interval}s..."
                )
                time.sleep(self.poll_interval)
            else:
                return


def kalshi(
    ticker: Optional[str] = None,
    tickers: Optional[str] = None,
    keyword: Optional[str] = None,
    series_ticker: Optional[str] = None,
    match_whole_word: bool = False,
    page_size: int = 200,
    max_scan_markets: int = 4000,
    max_scan_events: int = 8000,
    poll_interval: int = 60,
    page_delay_seconds: float = 0.2,
    event_expand_delay_seconds: float = 0.15,
    max_http_retries: int = 10,
    backoff_cap_seconds: float = 90.0,
    base_url: str = "https://external-api.kalshi.com/trade-api/v2",
    max_readings: Optional[int] = None,
) -> KalshiSource:
    return KalshiSource(
        ticker=ticker,
        tickers=tickers,
        keyword=keyword,
        series_ticker=series_ticker,
        match_whole_word=match_whole_word,
        page_size=page_size,
        max_scan_markets=max_scan_markets,
        max_scan_events=max_scan_events,
        poll_interval=poll_interval,
        page_delay_seconds=page_delay_seconds,
        event_expand_delay_seconds=event_expand_delay_seconds,
        max_http_retries=max_http_retries,
        backoff_cap_seconds=backoff_cap_seconds,
        base_url=base_url,
        max_readings=max_readings,
    )


if __name__ == "__main__":
    import os
    import sys

    if os.environ.get("KALSHI_TEST_DISCOVERY"):
        src = KalshiSource(
            series_ticker="KXWTI",
            poll_interval=0,
            max_readings=1,
        )
        n = 0
        for msg in src.run():
            print(msg["title"][:100])
            n += 1
            if n >= 3:
                break
        sys.exit(0)

    t = os.environ.get("KALSHI_TEST_TICKER")
    if not t:
        print("Set KALSHI_TEST_TICKER or KALSHI_TEST_DISCOVERY=1.")
        sys.exit(0)
    src = KalshiSource(ticker=t, poll_interval=0, max_readings=1)
    print(next(src.run()))
