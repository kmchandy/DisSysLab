from __future__ import annotations
from typing import Any, Dict, Iterable
import feedparser
from dsl.connector_lib.inputs.base import InputConnector


class InputConnectorRSS(InputConnector):
    """
    Read items from an RSS feed.

    Usage
    -----
    Send this command to the "in" port:
        {"cmd": "pull", "args": {"url": "<rss_url>"}}

    For each entry in the feed, the connector outputs:
        {"data": {"title": ..., "link": ..., "summary": ...}}

    Notes
    -----
    - Requires `feedparser` library. Install with:
          pip install feedparser
    - Great for news feeds, weather updates, sports, etc.
    """

    def _pull(self, cmd: str, args: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
        url = args.get("url")
        if not url:
            raise ValueError("InputConnectorRSS requires 'url' in args")

        feed = feedparser.parse(url)
        if feed.bozo:
            raise ValueError(f"Failed to parse RSS feed: {url}")

        for entry in feed.entries:
            yield {
                "title": entry.get("title", "(no title)"),
                "link": entry.get("link", ""),
                "summary": entry.get("summary", ""),
            }
