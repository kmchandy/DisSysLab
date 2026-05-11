# dissyslab/components/sinks/periodic_brief_sink.py

"""
PeriodicBriefSink — write a periodic morning briefing assembled from
multiple sources.

Use case: Pat wants ONE markdown artifact each morning that combines
calendar events, weather, important email summaries, and news
headlines. Multiple sources fan-in to this single sink; the sink
routes each message into the right section by its ``source`` (or
``type``) field, and rewrites the briefing file on every message.

By the time the office terminates, the file contains all the
material every source produced.

Routing
=======

Each incoming message is sorted into one of four buckets based on
the ``source`` or ``type`` field of the message:

- ``"gmail"`` → email bucket (these are already kept-and-summarised
  by an upstream ``mail_summariser`` role).
- ``"calendar"`` → calendar bucket.
- ``"weather"`` (in ``type`` field) → weather (one-of, latest wins).
- Anything else (RSS feed names like ``"bbc_world"``, ``"npr_news"``,
  ``"al_jazeera"``, etc.) → news bucket.

Output format
=============

A single markdown file with four section headers in this fixed
order, only included when their bucket has content:

```markdown
# Periodic brief — 2026-05-12

## Schedule
- 9am: 1:1 with Dana
- 11:30am: Client review

## Weather
Clear and 72°F in Pasadena, no rain expected.

## Email worth knowing about
- Acme invoice $1,200 due Friday. [open](https://mail.google.com/...)

## World
- UN Security Council to vote on Lebanon ceasefire. [bbc_world](https://...)
```

Used in office.md as
``Sinks: periodic_brief_sink(path="~/brief.md")``.
"""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


class PeriodicBriefSink:
    """Multi-source sink that assembles a periodic morning briefing."""

    def __init__(
        self,
        path: str = "brief.md",
        *,
        name: Optional[str] = None,
        title: Optional[str] = None,
    ):
        self.path = Path(os.path.expanduser(path)).resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)

        if title is None:
            title = f"Periodic brief — {datetime.now().strftime('%Y-%m-%d')}"
        self._title = title
        self._name = name or "periodic_brief_sink"

        # Per-section accumulators. Weather is one-of (latest wins);
        # the other three accumulate as lists.
        self._calendar: List[dict] = []
        self._weather: Optional[dict] = None
        self._email: List[dict] = []
        self._news: List[dict] = []

        # Write the initial header so a fresh file exists from t=0.
        self._rewrite()

    @property
    def __name__(self) -> str:
        return self._name

    def __call__(self, msg: Any) -> Any:
        """Route one message into its bucket; rewrite the briefing."""
        if not isinstance(msg, dict):
            # Unknown shape — skip silently. The sink never fails on
            # input it doesn't understand.
            return msg

        category = self._categorise(msg)
        if category == "calendar":
            self._calendar.append(msg)
        elif category == "weather":
            self._weather = msg
        elif category == "email":
            self._email.append(msg)
        elif category == "news":
            self._news.append(msg)
        # If category is None the message had no recognizable source;
        # drop it rather than mis-categorise.

        self._rewrite()
        return msg

    # The framework's Sink wrapper calls .run(msg); ``run`` is the
    # canonical entrypoint.
    run = __call__

    # ── Categorisation ───────────────────────────────────────────────

    @staticmethod
    def _categorise(msg: Dict[str, Any]) -> Optional[str]:
        """Return one of {calendar, weather, email, news, None}."""
        # Some sources tag with "source", others with "type".
        src = msg.get("source") or msg.get("type") or ""
        if not isinstance(src, str):
            return None
        s = src.lower()
        if "calendar" in s:
            return "calendar"
        if "weather" in s:
            return "weather"
        if "gmail" in s or s == "email":
            return "email"
        # Otherwise assume it's a news article (bbc_world, npr_news,
        # al_jazeera, hacker_news, techcrunch, etc.).
        if s:
            return "news"
        return None

    # ── Rendering ────────────────────────────────────────────────────

    def _rewrite(self) -> None:
        """Re-render the entire briefing to disk."""
        parts: List[str] = [f"# {self._title}", ""]

        if self._calendar:
            parts.append("## Schedule")
            parts.append("")
            for item in self._calendar:
                parts.append(self._render_calendar_item(item))
            parts.append("")

        if self._weather is not None:
            parts.append("## Weather")
            parts.append("")
            parts.append(self._render_weather(self._weather))
            parts.append("")

        if self._email:
            parts.append("## Email worth knowing about")
            parts.append("")
            for item in self._email:
                parts.append(self._render_email_item(item))
            parts.append("")

        if self._news:
            parts.append("## World")
            parts.append("")
            for item in self._news:
                parts.append(self._render_news_item(item))
            parts.append("")

        text = "\n".join(parts).rstrip() + "\n"
        self.path.write_text(text, encoding="utf-8")

    @staticmethod
    def _render_calendar_item(item: Dict[str, Any]) -> str:
        title = item.get("title") or "(untitled event)"
        ts = item.get("timestamp", "")
        if ts:
            return f"- {title}  *({ts})*"
        return f"- {title}"

    @staticmethod
    def _render_weather(item: Dict[str, Any]) -> str:
        title = item.get("title")
        if title:
            return str(title)
        city = item.get("city", "")
        temp_c = item.get("temp_c")
        cond = item.get("conditions", "")
        bits = []
        if cond:
            bits.append(cond)
        if temp_c is not None:
            bits.append(f"{temp_c}°C")
        if city:
            return f"{', '.join(bits)} in {city}."
        return ", ".join(bits) or "(weather data received)"

    @staticmethod
    def _render_email_item(item: Dict[str, Any]) -> str:
        headline = item.get("headline") or item.get("title") or "(no subject)"
        url = item.get("url", "")
        if url:
            return f"- {headline} [open]({url})"
        return f"- {headline}"

    @staticmethod
    def _render_news_item(item: Dict[str, Any]) -> str:
        # Prefer an upstream-written headline; fall back to the raw
        # title if no writer agent has produced one.
        headline = item.get("headline") or item.get("title") or "(untitled)"
        url = item.get("url", "")
        source = item.get("source", "")
        if url and source:
            return f"- {headline} [{source}]({url})"
        if url:
            return f"- {headline} [link]({url})"
        return f"- {headline}"

    def finalize(self) -> None:
        """Final flush. Idempotent; safe to call at office shutdown."""
        self._rewrite()
