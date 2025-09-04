from __future__ import annotations
from typing import Any, Dict, Iterable, List
import requests
import feedparser

from dsl.connector_lib.inputs.base import InputConnector

DEFAULT_UA = "DisSysLab/0.1 (+https://github.com/kmchandy/DisSysLab)"


class InputConnectorRSS(InputConnector):
    """
    Reads items from an RSS/Atom feed.

    Command:
      {"cmd": "pull", "args": {"url": "<rss_url>", "limit": 20}}

    Behavior:
      - Fetches with requests (custom User-Agent), parses with feedparser.
      - Emits one item per entry as:
          {"data": {"title": str, "link": str, "summary": str}}
      - If 'limit' provided, only the first N entries are emitted.
    """

    def _pull(self, cmd: str, args: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
        url = args.get("url")
        if not url or not isinstance(url, str):
            raise ValueError("InputConnectorRSS requires args['url'] (str)")

        limit = args.get("limit")
        if limit is not None:
            try:
                limit = int(limit)
            except Exception:
                raise ValueError(
                    "args['limit'] must be an integer if provided")

        # Fetch with a User-Agent to avoid being blocked
        resp = requests.get(
            url, headers={"User-Agent": DEFAULT_UA}, timeout=20)
        resp.raise_for_status()

        feed = feedparser.parse(resp.content)
        if feed.bozo:
            # bozo_exception may contain more detail
            raise ValueError(f"Failed to parse RSS feed: {url}")

        entries = feed.entries or []
        if limit is not None:
            entries = entries[:limit]

        for entry in entries:
            yield {
                "title": entry.get("title", "(no title)"),
                "link": entry.get("link", ""),
                "summary": entry.get("summary", ""),
            }
