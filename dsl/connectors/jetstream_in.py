# jetstream_in.py
from __future__ import annotations
import json
import time
import threading
import queue
import urllib.parse
from typing import Any, Dict, Iterable, Iterator, List, Optional, Sequence, Tuple, Set
import websocket  # pip install websocket-client


class Jetstream_In:
    """
    Lean Bluesky Jetstream source (JSON over WebSocket).

    • Connects to a Jetstream instance (default: US-West public).
    • Subscribes to desired collections (default: posts only).
    • Yields one dict per post create event (newest-first upstream; we stream as received).
    • Auto-reconnects with backoff; in-memory dedupe by (did, collection, rkey, rev).

    Docs / endpoints:
      - Public instances & /subscribe params (wantedCollections, cursor, etc.). 
      - Jetstream “commit” events with record.text/createdAt for posts. 
    """

    DEFAULT_URL = "wss://jetstream2.us-west.bsky.network/subscribe"
    UA = "DisSysLab Jetstream (you@example.com)"

    def __init__(
        self,
        *,
        url: str = DEFAULT_URL,
        wanted_collections: Sequence[str] = ("app.bsky.feed.post",),
        wanted_dids: Sequence[str] | None = None,
        cursor: int | None = None,           # unix microseconds
        life_time: float | None = None,      # None = run indefinitely
        queue_max: int = 1000,               # in-flight buffer
        dedupe_max: int = 20000,             # in-memory seen keys
        ping_interval: float = 10.0,         # seconds
        reconnect_backoff: Tuple[float, float, float] = (1.0, 2.0, 5.0),
        max_num_posts: int | None = None,    # stop after yielding N posts; None = forever
    ):
        self.url = url
        self.wanted_collections = list(wanted_collections or [])
        self.wanted_dids = list(wanted_dids or [])
        self.cursor = cursor
        self.life_time = life_time
        self.ping_interval = float(ping_interval)
        self.reconnect_backoff = reconnect_backoff

        self._q: "queue.Queue[dict]" = queue.Queue(maxsize=queue_max)
        self._stop = threading.Event()
        self._ws: websocket.WebSocketApp | None = None
        self._thread: threading.Thread | None = None
        self._seen: Set[Tuple[str, str, str, str]] = set()
        self._seen_order: List[Tuple[str, str, str, str]] = []
        self._dedupe_max = int(dedupe_max)
        self.max_num_posts = None if max_num_posts is None else int(
            max(0, max_num_posts))

    # ---- public iteration ----
    def __iter__(self) -> Iterator[Dict[str, Any]]:
        start = time.time()
        self._start_ws()
        count = 0  # count number of posts read
        try:
            while not self._stop.is_set():
                # life timer
                if self.life_time is not None and (time.time() - start) >= self.life_time:
                    break
                try:
                    item = self._q.get(timeout=0.5)
                except queue.Empty:
                    continue
                yield item
                count += 1
                # stop if we've reached the cap
                if self.max_num_posts is not None and count >= self.max_num_posts:
                    break
        finally:
            self.close()

    def run(self):
        """Iterator alias for parity with RSS_In: use for msg in jetstream.run(): ..."""
        return self.__iter__()

    # ---- lifecycle ----
    def close(self):
        self._stop.set()
        try:
            if self._ws:
                try:
                    self._ws.close()
                except Exception:
                    pass
        finally:
            if self._thread and self._thread.is_alive():
                self._thread.join(timeout=2.0)

    # ---- websocket management ----
    def _start_ws(self):
        # Build query
        qs: list[tuple[str, str]] = []
        for c in self.wanted_collections:
            qs.append(("wantedCollections", c))
        for d in self.wanted_dids:
            qs.append(("wantedDids", d))
        if self.cursor is not None:
            qs.append(("cursor", str(self.cursor)))
        full_url = self.url + "?" + \
            urllib.parse.urlencode(qs, doseq=True) if qs else self.url

        headers = [
            ("User-Agent", self.UA),
        ]

        def on_message(ws, message: str):
            self._handle_message(message)

        def on_error(ws, err):
            # Push a lightweight diagnostic; don’t spam
            # You can log to stderr if needed.
            pass

        def on_close(ws, code, msg):
            # Signal end-of-connection; iterator loop will trigger reconnect
            pass

        def run():
            backoffs = list(self.reconnect_backoff)
            while not self._stop.is_set():
                try:
                    self._ws = websocket.WebSocketApp(
                        full_url,
                        header=[f"{k}: {v}" for k, v in headers],
                        on_message=on_message,
                        on_error=on_error,
                        on_close=on_close,
                    )
                    self._ws.run_forever(
                        ping_interval=self.ping_interval,
                        ping_timeout=max(5.0, self.ping_interval / 2),
                        http_proxy_host=None,
                        http_proxy_port=None,
                        origin=None,
                    )
                except Exception:
                    pass
                if self._stop.is_set():
                    break
                # backoff
                delay = backoffs[0]
                time.sleep(delay)
                # increase gradually up to max
                if len(backoffs) > 1:
                    backoffs = backoffs[1:] + [backoffs[-1]]

        self._thread = threading.Thread(
            target=run, name="JetstreamWS", daemon=True)
        self._thread.start()

    # ---- event handling ----
    def _handle_message(self, msg: str):
        try:
            ev = json.loads(msg)
        except Exception:
            return

        # Only process commit/create for the desired collection(s)
        if ev.get("kind") != "commit":
            return
        commit = ev.get("commit") or {}
        if commit.get("operation") != "create":
            return
        collection = commit.get("collection") or ""
        if collection not in self.wanted_collections:
            # Jetstream already filters, but keep this guard
            return

        did = ev.get("did") or ""
        rkey = commit.get("rkey") or ""
        rev = commit.get("rev") or ""
        key = (did, collection, rkey, rev)
        if key in self._seen:
            return
        self._remember(key)

        record = commit.get("record") or {}
        # posts have record["text"], record["createdAt"], optional record["facets"], record["langs"]
        text = (record.get("text") or "").strip()
        created_at = record.get("createdAt") or None
        facets = record.get("facets") or None
        langs = record.get("langs") or record.get("languageTags") or None

        out = {
            "text": text,
            "created_at": created_at,
            "did": did,
            "uri": f"at://{did}/{collection}/{rkey}" if (did and rkey) else None,
            "time_us": ev.get("time_us"),
        }
        if facets:
            out["facets"] = facets
        if langs:
            out["lang"] = langs

        # Non-blocking put; drop if queue is full (keeps stream moving)
        try:
            self._q.put_nowait(out)
        except queue.Full:
            pass

    def _remember(self, key: Tuple[str, str, str, str]):
        self._seen.add(key)
        self._seen_order.append(key)
        if len(self._seen_order) > self._dedupe_max:
            old = self._seen_order.pop(0)
            self._seen.discard(old)
