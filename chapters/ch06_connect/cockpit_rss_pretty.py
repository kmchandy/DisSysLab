"""
Cockpit RSS Demo (Pretty Console)
=================================

A tiny "cockpit" that pulls an RSS feed, enriches items a bit, batches them,
and prints **colorful, multi-line panels** to your terminal.

Pipeline:
    RSS -> Transformer (title/link/meta) -> Batch (every N) -> ConsolePrettyPrinter

What you’ll see:
- Panels with a title, count, timestamp
- Each item as 3 lines: Title (bold cyan), Link (blue underline), Meta (dim)
- A small "🔥" prefix for titles that look hot (keyword hint)

Run:
    python dsl/examples/ch06_connect/cockpit_rss_pretty.py

No API keys, no OAuth. Just works.
"""

from __future__ import annotations
from typing import Any, Dict
from urllib.parse import urlparse
from email.utils import parsedate_to_datetime
from datetime import datetime, timezone

from dsl.core import Network
from dsl.block_lib.stream_generators import GenerateFromList
from dsl.block_lib.stream_transformers import TransformerFunction
from dsl.connector_lib.inputs.rss import InputConnectorRSS   # <— your RSS connector
from dsl.connector_lib.outputs import BatchOutput
# <— multi-line, colorful
from dsl.connector_lib.outputs.console_pretty import ConsolePrettyPrinter

# Pick a recognizable feed. Change to any RSS URL you like.
RSS_URL = "https://www.espn.com/espn/rss/news"
# Other ideas:
#   "https://news.ycombinator.com/rss"
#   "https://www.theverge.com/rss/index.xml"
#   "https://www.nasa.gov/news-release/feed/"


def _domain(link: str) -> str:
    """Return the website domain (e.g., 'espn.com') from a URL."""
    try:
        return urlparse(link).netloc.replace("www.", "")
    except Exception:
        return "unknown"


def _age(published: str | None) -> str:
    """
    Convert an RSS 'pubDate' string to a friendly age like '2h ago' or '3d ago'.
    Uses email.utils.parsedate_to_datetime for common RSS date formats.
    """
    if not published:
        return "now"
    try:
        dt = parsedate_to_datetime(published)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        delta = now - dt
        s = int(delta.total_seconds())
        if s < 60:
            return f"{s}s ago"
        m = s // 60
        if m < 60:
            return f"{m}m ago"
        h = m // 60
        if h < 24:
            return f"{h}h ago"
        d = h // 24
        return f"{d}d ago"
    except Exception:
        return "recent"


# Tiny "hotness" heuristic: add 🔥 if the title contains these
HOT_WORDS = ("ai", "security", "research", "paper", "launch",
             "openai", "model", "funding", "breach")


def to_row_structured(msg: Dict[str, Any]) -> Dict[str, Dict[str, str]]:
    """
    Input message shape from InputConnectorRSS:
        {"data": {"title": ..., "link": ..., "published": ...}}

    Output (structured row for ConsolePrettyPrinter):
        {"row": {"title": "...", "link": "...", "meta": "..."}}
    """
    item = msg.get("data", {}) or {}

    title = str(item.get("title", "Untitled")).strip()
    link = str(item.get("link", "")).strip()

    dom = _domain(link)
    age = _age(item.get("published"))

    # Add a tiny "🔥" prefix if looks interesting
    hot = any(w in title.lower() for w in HOT_WORDS)
    title_display = ("🔥 " if hot else "• ") + title

    return {
        "row": {
            "title": title_display,            # line 1 (bold cyan)
            "link": link,                      # line 2 (blue underline)
            "meta": f"{dom} • {age}",          # line 3 (dim)
        }
    }


def build_network() -> Network:
    """
    Pull up to 24 RSS items -> make pretty rows -> batch every 8 -> print panels.
    """
    return Network(
        blocks={
            # Send a single "pull" command to the RSS connector
            "pull": GenerateFromList(
                items=[{"cmd": "pull", "args": {"url": RSS_URL, "limit": 24}}],
                delay=0.02,  # small delay gives a pleasant cadence to panels
            ),

            # Input connector: emits {"data": {...}} per item
            "rss": InputConnectorRSS(),

            # Transform each item to {"row": {"title","link","meta"}}
            "row": TransformerFunction(func=to_row_structured),

            # Batch every N rows (change N to taste)
            "batch": BatchOutput(
                N=8,
                meta_builder=lambda buf: {"title": "DisSysLab RSS -> Cockpit"},
            ),

            # Pretty console sink: 3-line rows, colored
            "console": ConsolePrettyPrinter(sample_size=8, title_fallback="DisSysLab Cockpit"),
        },
        connections=[
            ("pull", "out", "rss", "in"),
            ("rss", "out", "row", "in"),
            ("row", "out", "batch", "in"),
            ("batch", "out", "console", "in"),
        ],
    )


if __name__ == "__main__":
    net = build_network()
    net.compile_and_run()
