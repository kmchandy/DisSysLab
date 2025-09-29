# dsl/connectors/rss.py
from __future__ import annotations

from typing import Any


def parse(url: str) -> Any:
    """
    Parse an RSS/Atom feed. Requires `feedparser` (optional dependency).

    Install:
        pip install feedparser
    """
    try:
        import feedparser  # type: ignore
    except Exception as e:  # pragma: no cover
        raise RuntimeError(
            "feedparser not installed; run: pip install feedparser") from e
    return feedparser.parse(url)
