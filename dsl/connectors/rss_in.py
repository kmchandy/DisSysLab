# modules/connectors/rss_in.py
#
# Minimal RSS/Atom poller for teaching.
# - item-only emits (one dict per new entry)
# - optional linked-page fetch to get page_text
# - simple de-dupe per process
#
# Requires: feedparser, requests, beautifulsoup4

"""
RSS_In — Minimal, example-first connector

Who this is for
---------------
People who know basic Python and can ask an LLM to scaffold new connectors.
This file is intentionally small and “good enough” for demos, not a full library.

What it does (in one sentence)
------------------------------
Poll an RSS/Atom URL every N seconds and yield one dict per new entry (“item” mode only).

Interface contract (stable across our connectors)
-------------------------------------------------
- Zero-arg source function calls `connector.run()` (an iterator/generator)
- Yields plain Python dicts (keys are up to the connector)
- Works with the DSL by wiring:  network([(source_fn, sink_fn)])

Quick start (pattern)
---------------------
# 1) Configure:
rss = RSS_In(
    url="https://www.nasa.gov/feed/",
    poll_seconds=4,           # watchable pace
    life_time=20,             # stop after ~20s (None to run forever)
    fetch_page=True,          # optional: fetch linked article text
    output_keys=["title","link","summary","updated","page_text"],
)

# 2) Source function:
def from_rss():
    for item in rss.run():
        # keep the message small for sinks
        yield {"title": item.get("title"), "page_text": item.get("page_text")}

# 3) Wire to a sink (e.g., live_kv_console) in your module’s runner.

Copy-and-adapt checklist (5 mins)
---------------------------------
1) **Duplicate this file** → rename class & filename (e.g., `MyAPI_In`).
2) **Keep the interface**: `__init__(config…)` + `run()` yielding dicts.
3) **Replace `_poll_once()`** with your data fetch:
   - REST: `requests.get()`, parse JSON, build dicts
   - Websocket: `websockets` (bridge to yield dicts)
   - Local files: iterate CSV rows (see ReplayCSV_In)
4) **Keep messages small**: choose 3–6 fields; add `output_keys` if useful.
5) **Be a good citizen**: set a descriptive User-Agent, add timeouts, cap bytes.

Common customizations
---------------------
- Pace & duration: `poll_seconds`, `life_time`
- Include article text: `fetch_page=True`
- Trim fields: `output_keys=[…]`
- Dedupe heuristic: edit `_entry_key()` (id→link→title precedence)

Smoke tests (before wiring to DSL)
----------------------------------
- Print first 3 emitted items:
    for i, it in zip(range(3), rss.run()): print(it)
- Verify keys match your sink’s expectations (e.g., "title", "page_text").

Gotchas
-------
- Some feeds reuse titles → the `_entry_key()` dedupe prefers id/link to avoid repeats.
- Feeds can be slow; if nothing appears immediately, extend `life_time` or try another URL.
- Large pages: `fetch_max_bytes` protects you; keep it modest for demos.

Contributing
------------
This connector is an **example**, not exhaustive. Build your own by copying the pattern,
then ask your LLM for scaffolding where needed. Keep the run() → dicts contract intact.
"""


from __future__ import annotations
import time
import feedparser
import requests
from bs4 import BeautifulSoup
from typing import Dict, Any, List, Optional, Iterator


class RSS_In:
    def __init__(
        self,
        *,
        url: str,
        poll_seconds: float = 3.0,
        life_time: Optional[float] = 30.0,
        # e.g. ["title","link","page_text"]
        output_keys: Optional[List[str]] = None,
        fetch_page: bool = False,
        fetch_timeout: float = 8.0,
        fetch_max_bytes: int = 500_000,
        user_agent: str = "Modules RSS (contact@example.com)",
    ):
        self.url = url
        self.poll_seconds = float(poll_seconds)
        self.life_time = life_time
        self.output_keys = output_keys
        self.fetch_page = fetch_page
        self.fetch_timeout = float(fetch_timeout)
        self.fetch_max_bytes = int(fetch_max_bytes)
        self.headers_feed = {"User-Agent": user_agent}
        self.headers_page = {"User-Agent": user_agent,
                             "Accept": "text/html,*/*;q=0.8"}
        self._seen: set = set()  # simple per-process de-dupe

    # public API used by modules: zero-arg iterator
    def run(self) -> Iterator[Dict[str, Any]]:
        start = time.time()
        while True:
            # stop condition
            if self.life_time is not None and (time.time() - start) >= self.life_time:
                break

            # poll once and emit each new item
            for item in self._poll_once():
                yield item

            time.sleep(self.poll_seconds)

    # internal: one poll → list of new items (dicts)
    def _poll_once(self) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        feed = feedparser.parse(self.url, request_headers=self.headers_feed)
        entries = list(getattr(feed, "entries", []) or [])

        # newest first if possible
        try:
            entries.sort(key=lambda e: getattr(e, "updated_parsed", None) or getattr(
                e, "published_parsed", None), reverse=True)
        except Exception:
            pass

        for e in entries:
            key = self._entry_key(e)
            if key in self._seen:
                continue
            self._seen.add(key)

            item = self._normalize_entry(e)

            if self.fetch_page and item.get("link"):
                item.update(self._fetch_page(item["link"]))

            if self.output_keys:
                item = {k: item.get(k) for k in self.output_keys}

            out.append(item)

        return out

    # prefer id → link → title → repr
    def _entry_key(self, e: Any):
        if getattr(e, "id", None):
            return ("id", e.id)
        link = getattr(e, "link", None)
        if link:
            return ("link", link)
        title = getattr(e, "title", None)
        if title:
            return ("title", title)
        return ("repr", repr(e))

    # convert feedparser entry to a plain dict with a couple of common fields
    def _normalize_entry(self, e: Any) -> Dict[str, Any]:
        d: Dict[str, Any] = {}
        d["title"] = getattr(e, "title", None)
        d["link"] = getattr(e, "link", None)
        # pass through a best-effort timestamp (don’t normalize; keep it simple)
        d["updated"] = getattr(e, "updated", None) or getattr(
            e, "published", None)
        # include summary text when available
        d["summary"] = getattr(e, "summary", None)
        return d

    def _fetch_page(self, url: str) -> Dict[str, Any]:
        meta = {"page_text": "", "page_status": None,
                "page_content_type": None}
        try:
            with requests.get(url, headers=self.headers_page, timeout=self.fetch_timeout, stream=True) as r:
                meta["page_status"] = r.status_code
                meta["page_content_type"] = r.headers.get("Content-Type", "")
                chunks, total = [], 0
                for chunk in r.iter_content(16384):
                    if not chunk:
                        break
                    chunks.append(chunk)
                    total += len(chunk)
                    if total >= self.fetch_max_bytes:
                        break
                html = b"".join(chunks).decode("utf-8", errors="replace")
            soup = BeautifulSoup(html, "html.parser")
            for tag in soup(["script", "style", "noscript"]):
                tag.decompose()
            text = " ".join(soup.get_text(" ").split())
            meta["page_text"] = text[:200_000]
        except Exception as ex:
            meta["page_text"] = f"[fetch_error] {type(ex).__name__}: {ex}"
        return meta
