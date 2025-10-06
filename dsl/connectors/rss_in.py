# dsl.connectors.rss_in

# Requires: feedparser, requests, beautifulsoup4

from __future__ import annotations
import time
import feedparser
import requests
import warnings
import re
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning
from typing import Dict, Any, List, Optional, Union, Iterator
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime


class RSS_In:
    """
    Lean RSS/Atom poller with optional linked-page fetch.

    Behavior
    -------
    • Polls `url` every `poll_seconds`.
    • Emits either single items (“item”) or batches (“batch”).
      - In "batch" mode, a flush happens when the buffer reaches `batch_size`
        or `batch_seconds` have elapsed since the last flush.
    • Normalizes item time to UTC ISO-8601 (key: "time") using entry.updated/published.
    • First fetch allows a backfill (ignores `since` so the screen isn’t empty);
      after accepting new items, the internal lower bound is set to the newest item.
    • Per-process de-duplication by entry id → (title, link) → title → link.

    Class attributes (HTTP headers)
    ------------------------------
    HEADERS_FEED: dict
        Headers for the **feed** request. Set a descriptive User-Agent with a
        contact email or URL to avoid throttling (e.g., NWS/SEC feeds).
    HEADERS_PAGE: dict
        Headers for **linked page** fetches (when `fetch_page=True`).
        Includes a UA and broad Accept for HTML/XML.

    Parameters
    ----------
    url : str
        RSS/Atom feed URL to poll.
    poll_seconds : float, default 1.0
        Seconds to sleep between polls. Lower = more frequent checks.
    emit_mode : str, default "item"
        Emission mode:
          - "item": yield one dict per new entry.
          - "batch": yield a list[dict] on each flush.
    batch_size : int, default 4
        In "batch" mode, minimum number of buffered items needed to trigger a flush.
        Ignored in "item" mode. Use ≥1.
    batch_seconds : float, default 5.0
        In "batch" mode, time-based flush interval. If any items are buffered and
        this much time has elapsed since the last flush, emit the batch.
    life_time : float | None, default 300.0
        Total run time (seconds) before the iterator stops. Use None to run forever.
        On stop, a **final flush** occurs in "batch" mode if items are buffered.
    since : str | datetime | None, default None
        Lower time bound for “new” entries. Accepts RFC-822 strings (e.g., from feeds)
        or ISO-8601 (with or without 'Z'). Naive datetimes are treated as UTC.
        NOTE: On the **first fetch**, this bound is ignored to allow backfill; after
        accepting items, the internal bound is set to the newest item’s time.
    output_keys : list[str] | None, default None
        If provided, each emitted item is reduced to only these keys
        (the normalized "time" key is also included even if not listed).
        Example: ["id", "title", "link", "time", "page_text"].
    fetch_page : bool, default False
        If True, fetches each item’s `link` URL and attaches page metadata/text:
          - "page_status" (HTTP status), "page_content_type", "page_text" (plain text, truncated).
        Useful when the LLM agent needs the article body.
    fetch_timeout : float, default 10.0
        Per-request timeout (seconds) for linked page fetches.
    fetch_max_bytes : int, default 1_000_000
        Maximum bytes to download from each linked page (safety cap). Also bounds
        the size of stored/extracted text.

    Yields
    ------
    dict
        When `emit_mode="item"`, yields one dict per new entry.
    list[dict]
        When `emit_mode="batch"`, yields a list of dicts on each flush.

    Item Fields
    -----------
    By default, an item includes all keys provided by `feedparser` for the entry,
    plus a normalized UTC "time". If `output_keys` is set, the item is pruned to
    those keys (and "time").

    Example
    -------
    >>> rss = RSS_In(
    ...     url="https://api.weather.gov/alerts/active.atom",
    ...     emit_mode="item",
    ...     fetch_page=True,
    ...     output_keys=["title","link","time","page_text"],
    ... )
    >>> for item in rss:
    ...     print(item["time"], item["title"])
    """
    HEADERS_FEED = {"User-Agent": "DisSysLab RSS (you@example.com)"}
    HEADERS_PAGE = {
        "User-Agent": "DisSysLab Fetcher (you@example.com)",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    def __init__(
        self,
        *,
        url: str,
        poll_seconds: float = 1.0,
        emit_mode: str = "item",     # "item" or "batch"
        batch_size: int = 4,
        batch_seconds: float = 5.0,
        life_time: Optional[float] = 300.0,
        since: Optional[Union[str, datetime]] = None,  # None = no lower bound
        # e.g., ["id","title","link","time","page_text"]
        output_keys: Optional[List[str]] = None,
        fetch_page: bool = False,
        fetch_timeout: float = 10.0,
        fetch_max_bytes: int = 1_000_000,
    ):
        self.url = url
        self.poll_seconds = float(poll_seconds)
        self.emit_mode = emit_mode
        self.batch_size = int(batch_size)
        self.batch_seconds = float(batch_seconds)
        self.life_time = life_time
        self.output_keys = output_keys
        self.fetch_page = fetch_page
        self.fetch_timeout = float(fetch_timeout)
        self.fetch_max_bytes = int(fetch_max_bytes)

        self._since_dt = self._parse_since(since)
        self._first_fetch = True
        self._seen: set = set()
        self._buf: List[Dict[str, Any]] = []
        self._last_flush = time.time()

        self._seen_titles = set()   # normalized titles we've already emitted

    def _gen(self) -> Iterator[Union[Dict[str, Any], List[Dict[str, Any]]]]:
        start = time.time()
        while True:
            for p in self._poll_once():
                yield p
            if self.life_time is not None and (time.time() - start) >= self.life_time:
                # final flush
                if self.emit_mode == "batch" and self._buf:
                    out = list(self._buf)
                    self._buf.clear()
                    yield out
                break
            time.sleep(self.poll_seconds)

    def __iter__(self):
        # useful for Pythonic iterator
        return self._gen()

    def run(self):
        # alias because all sources use run
        return self._gen()

    # -------- internals --------

    def _poll_once(self) -> List[Union[Dict[str, Any], List[Dict[str, Any]]]]:
        out: List[Union[Dict[str, Any], List[Dict[str, Any]]]] = []
        feed = feedparser.parse(self.url, request_headers=self.HEADERS_FEED)
        entries = getattr(feed, "entries", []) or []

        # sort newest → oldest
        entries.sort(key=self._entry_dt_key, reverse=True)

        new_items: List[Dict[str, Any]] = []
        for e in entries:
            if not self._is_new_enough(e):
                continue
            key = self._entry_key(e)
            if key in self._seen:
                continue
            # --- identical-title suppressor ---
            tn = self._norm_title(self._get_title(e))
            if tn and tn in self._seen_titles:
                continue
            self._seen.add(key)

            item = self._normalize_entry(e)
            if self.fetch_page and item.get("link"):
                item.update(self._fetch_page(item["link"]))
            new_items.append(item)

            # mark title as seen
            if tn:
                self._seen_titles.add(tn)

        if new_items:
            newest_dt = self._entry_dt(new_items[0])
            if newest_dt:
                self._since_dt = newest_dt

        # emit
        now = time.time()
        if self.emit_mode == "item":
            out.extend(new_items)
        else:
            self._buf.extend(new_items)
            by_size = len(self._buf) >= max(1, self.batch_size)
            by_time = (now - self._last_flush) >= self.batch_seconds
            if self._buf and (by_size or by_time):
                out.append(list(self._buf))
                self._buf.clear()
                self._last_flush = now

        self._first_fetch = False
        return out

    def _parse_since(self, s: Optional[Union[str, datetime]]) -> Optional[datetime]:
        if s is None:
            return None
        if isinstance(s, datetime):
            return s.astimezone(timezone.utc) if s.tzinfo else s.replace(tzinfo=timezone.utc)
        txt = str(s).strip().replace("Z", "+00:00")
        for parser in (self._parse_rfc822, self._parse_iso):
            dt = parser(txt)
            if dt:
                return dt
        return None

    @staticmethod
    def _parse_rfc822(txt: str) -> Optional[datetime]:
        try:
            return parsedate_to_datetime(txt).astimezone(timezone.utc)
        except Exception:
            return None

    @staticmethod
    def _parse_iso(txt: str) -> Optional[datetime]:
        try:
            return datetime.fromisoformat(txt).astimezone(timezone.utc)
        except Exception:
            return None

    def _entry_dt_key(self, e: Any) -> float:
        dt = self._entry_dt(e)
        return dt.timestamp() if dt else 0.0

    def _entry_dt(self, e: Any) -> Optional[datetime]:
        # prefer 'updated' then 'published' (string fields)
        s = getattr(e, "updated", None) or getattr(e, "published", None)
        if not s and isinstance(e, dict):
            s = e.get("updated") or e.get("published")
        if not s:
            return None
        for parser in (self._parse_rfc822, self._parse_iso):
            dt = parser(str(s).replace("Z", "+00:00"))
            if dt:
                return dt
        return None

    def _is_new_enough(self, e: Any) -> bool:
        if self._first_fetch:  # allow initial backfill so the demo shows data
            return True
        if self._since_dt is None:
            return True
        dt = self._entry_dt(e)
        return (dt is not None) and (dt > self._since_dt)

    def _entry_key(self, e: Any) -> Any:
        # id → (title,link) → title → link → repr
        if hasattr(e, "id") and getattr(e, "id"):
            return ("id", e.id)
        title = getattr(e, "title", None)
        link = getattr(e, "link", None)
        if not title and isinstance(e, dict):
            title = e.get("title")
        if not link and isinstance(e, dict):
            link = e.get("link")
        if title and link:
            return ("title+link", title, link)
        if title:
            return ("title", title)
        if link:
            return ("link", link)
        return ("repr", repr(e))

    def _normalize_entry(self, e: Any) -> Dict[str, Any]:
        d = dict(e)
        dt = self._entry_dt(e)
        d["time"] = dt.isoformat().replace("+00:00", "Z") if dt else None
        if self.output_keys:
            out = {}
            for k in self.output_keys:
                if k == "time":
                    out["time"] = d.get("time")
                elif k in d:
                    out[k] = d[k]
            return out
        return d

    def _get_title(self, e) -> str | None:
        t = getattr(e, "title", None)
        if t is None and isinstance(e, dict):
            t = e.get("title")
        return t

    def _norm_title(self, t: str | None) -> str | None:
        if not t:
            return None
        # collapse spaces, lowercase
        return " ".join(t.split()).strip().lower()

    def _fetch_page(self, url: str) -> Dict[str, Any]:
        meta: Dict[str, Any] = {"page_status": None,
                                "page_content_type": None, "page_text": ""}
        try:
            with requests.get(url, headers=self.HEADERS_PAGE, timeout=self.fetch_timeout, stream=True) as r:
                meta["page_status"] = r.status_code
                ctype = r.headers.get("Content-Type", "") or ""
                meta["page_content_type"] = ctype

                chunks, total = [], 0
                for chunk in r.iter_content(8192):
                    if not chunk:
                        break
                    chunks.append(chunk)
                    total += len(chunk)
                    if total >= self.fetch_max_bytes:
                        break
                raw = b"".join(chunks)

            # Parse text with XML parser when appropriate (prevents XMLParsedAsHTMLWarning)
            meta["page_text"] = self._extract_text(raw, ctype, url)

        except Exception as ex:
            meta["page_text"] = f"[fetch_error] {type(ex).__name__}: {ex}"
        return meta

    def _extract_text(self, raw: bytes, content_type: str, url: str) -> str:
        try:
            html = raw.decode("utf-8", errors="replace")
            # Decide parser
            is_xml = ("xml" in content_type.lower()) or url.lower().endswith(
                (".xml", ".atom", ".rss", ".xbrl"))
            # use lxml-xml if installed; else "xml"
            parser = "lxml-xml" if is_xml else "html.parser"

            if is_xml and parser == "lxml-xml":
                # no warning with XML parser
                soup = BeautifulSoup(html, "lxml-xml")
            elif is_xml:
                # fallback XML parser; silence bs4’s XMLParsedAsHTMLWarning just in case
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", XMLParsedAsHTMLWarning)
                    soup = BeautifulSoup(html, "xml")
            else:
                soup = BeautifulSoup(html, "html.parser")

            for tag in soup(["script", "style", "noscript"]):
                tag.extract()
            text = " ".join(soup.get_text(" ").split())
            return text[:200_000]
        except Exception:
            return ""
