"""
Cockpit RSS Demo
================

A tiny "live" console that feels like a cockpit:
RSS feed -> transform to pretty rows -> batch -> pretty console panels.

What you'll see:
- Panels that show a title, item count, timestamp, and a few example rows.
- Rows look like: "🔥 [Title](link) — domain • 2h ago"
- Flushes happen every N items (tweak N to change the rhythm).

Run:
    python dsl/examples/ch06_connect/cockpit_rss_demo.py

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
from dsl.connector_lib.inputs.rss import InputConnectorRSS
from dsl.connector_lib.outputs import BatchOutput, ConsoleFlushPrinter


# --- Choose any RSS feed. Examples are:
RSS_URL = "https://www.espn.com/espn/rss/news"
#   "https://news.ycombinator.com/rss"
#   "https://www.theverge.com/rss/index.xml"
#   "https://www.espn.com/espn/rss/news"
#   "https://www.nasa.gov/news-release/feed/"


def _domain(link: str) -> str:
    try:
        return urlparse(link).netloc.replace("www.", "")
    except Exception:
        return "unknown"


def _age(published: str | None) -> str:
    """
    Convert RSS pubDate to a friendly "age" string like '2h ago' or '3d ago'.
    Works with common RSS date formats via email.utils.parsedate_to_datetime.
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


HOT_WORDS = ("ai", "security", "research", "paper", "launch",
             "openai", "model", "funding", "breach")


def to_row(msg: Dict[str, Any]) -> Dict[str, str]:
    """
    Input:  {"data": {"title": ..., "link": ..., "published": ...}}
    Output: {"row": "🔥 [Title](link) — domain • 2h ago"}
    """
    item = msg.get("data", {}) or {}
    title = str(item.get("title", "Untitled")).strip()
    link = str(item.get("link", "")).strip()
    age = _age(item.get("published"))
    dom = _domain(link)

    # A tiny "hotness" hint: 🔥 if title contains certain keywords
    lower = title.lower()
    hot = any(w in lower for w in HOT_WORDS)
    prefix = "🔥 " if hot else "• "

    # Make a neat Markdown row (ConsoleFlushPrinter will render the text nicely)
    if link:
        body = f"[{title}]({link}) — {dom} • {age}"
    else:
        body = f"{title} — {dom} • {age}"

    return {"row": prefix + body}


def build_network() -> Network:
    """
    Pull N items from RSS → transform → batch every K items → pretty console.
    """
    return Network(
        blocks={
            # One "pull" command to fetch the feed. Limit keeps the demo snappy.
            "pull": GenerateFromList(
                items=[{"cmd": "pull", "args": {"url": RSS_URL, "limit": 24}}],
                delay=0.02,  # small delay makes the panels appear with a nice cadence
            ),

            # Input connector: yields {"data": {...}} per RSS item
            "rss": InputConnectorRSS(),

            # Enrich items into pretty console rows
            "row": TransformerFunction(func=to_row),

            # Batch flush every K rows (change N to see more/less frequent panels)
            "batch": BatchOutput(
                N=8,
                meta_builder=lambda buf: {"title": "DisSysLab RSS->Cockpit"},
            ),

            # Console sink: prints a nice panel per flush
            "console": ConsoleFlushPrinter(sample_size=8, title_fallback="DisSysLab RSS->Cockpit"),
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
