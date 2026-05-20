# dissyslab/components/sinks/intelligence_display.py

"""
IntelligenceDisplay: Rich console sink for intelligence briefing offices.

Displays each briefing note as a color-coded bordered block.
In Situation Room mode (max_items set), refreshes the display in place
showing the last N items — like a live dashboard.
"""

import json
import os
import re
from datetime import datetime

from dissyslab.components.sinks.message_coerce import (
    coerce_sink_message,
    normalize_multibullet_lines,
)

# Same prefix as custom_app backend ``APP_OUTPUT_PREFIX`` — one JSON line → SSE ``block``.
_APP_SSE_PREFIX = "__DSLAPP__:"

# ANSI color codes — no extra libraries needed
RED = "\033[91m"
YELLOW = "\033[93m"
GREEN = "\033[92m"
WHITE = "\033[97m"
GREY = "\033[90m"
RESET = "\033[0m"
BOLD = "\033[1m"
CLEAR = "\033[2J\033[H"   # Clear screen, move cursor to top

SIGNIFICANCE_COLOR = {
    "CRITICAL": RED,
    "HIGH":     YELLOW,
    "MEDIUM":   GREEN,
    "LOW":      WHITE,
}

WIDTH = 66

# Use "Apply" only when URL / body looks like a job or application flow; otherwise "Link".
_APPLY_URL_HINT = re.compile(
    r"(/jobs/|/job/|/careers|apply\.|/apply\b|greenhouse\.|boards\.greenhouse|lever\.co|"
    r"ashbyhq|workday\.com|myworkdayjobs|icims\.com|taleo\.|smartrecruiters|"
    r"indeed\.com/(?:rc/|viewjob)|linkedin\.com/jobs)",
    re.I,
)


def _markdown_link_append(text: str, url: str) -> str:
    """Return a markdown line for a supplementary URL (neutral label by default)."""
    if not url or url in text:
        return ""
    blob = f"{url}\n{text}"
    label = "Apply" if _APPLY_URL_HINT.search(blob) else "Link"
    return f"\n\n**{label}:** [{url}]({url})"


class IntelligenceDisplay:
    """
    Sink that prints each briefing note as a rich bordered console block.

    Args:
        max_items: If set, refreshes display in place showing last N items
                   (Situation Room mode). If None, scrolls continuously.
    """

    def __init__(self, max_items=None):
        self.max_items = max_items
        self.items = []   # rolling buffer
        self.count = 0

    def _app_sse_enabled(self) -> bool:
        return os.environ.get("DISSYSLAB_APP_SSE", "").strip().lower() in (
            "1",
            "true",
            "yes",
        )

    def _emit_app_markdown(self, body: str) -> None:
        """Single-line JSON for the custom app SSE Activity panel (no ANSI)."""
        line = _APP_SSE_PREFIX + json.dumps(
            {"t": "markdown", "body": body},
            ensure_ascii=False,
        )
        print(line, flush=True)

    def _item_to_markdown(self, item: dict) -> str:
        """Plain Markdown card for web UI / email-like readability."""
        significance = str(item.get("significance", "LOW")).upper()
        title = (item.get("title") or "").strip()
        text = normalize_multibullet_lines((item.get("text") or "").strip())
        url = (item.get("url") or "").strip()
        source = (item.get("source") or "").strip()

        parts: list[str] = []
        # Matcher prompts use bullet "•" blocks — show as-is with light framing.
        if text.startswith("•") or "\n•" in text[:400]:
            if title:
                parts.append(f"## {title}")
                parts.append("")
            parts.append(text)
            if source and source not in ("agent", "unknown"):
                parts.append("")
                parts.append(f"_Source: {source}_")
        else:
            if title:
                parts.append(f"## {title}")
                parts.append("")
            parts.append(f"**Significance:** {significance}")
            parts.append("")
            if text:
                parts.append(text)
        if url and url not in text:
            extra = _markdown_link_append(text, url).strip()
            if extra:
                parts.append(extra)
        out = "\n".join(parts).strip()
        return out or "_No briefing content._"

    def _format_item(self, item):
        """Format one briefing item as a list of display lines."""
        item = coerce_sink_message(item)
        significance = item.get("significance", "LOW").upper()
        source = item.get("source", "unknown")
        title = item.get("title", item.get("text", "")[:60])
        text = item.get("text", "")
        url = item.get("url", "")
        timestamp = item.get("timestamp", "")
        author = item.get("author", "")

        color = SIGNIFICANCE_COLOR.get(significance, WHITE)

        # Show @author for BlueSky, source name for RSS
        source_label = f"@{author[:15]}" if source == "bluesky" else source[:20]

        # Wrap text to two lines
        words = text.split()
        line = ""
        lines = []
        for word in words:
            if len(line) + len(word) + 1 <= WIDTH - 4:
                line += ("" if not line else " ") + word
            else:
                lines.append(line)
                line = word
            if len(lines) == 2:
                break
        if line and len(lines) < 2:
            lines.append(line)
        summary_lines = lines[:2]

        bar = "═" * WIDTH
        thin = "─" * WIDTH

        out = []
        out.append(f"{GREY}╔{bar}╗{RESET}")
        out.append(
            f"{GREY}║{RESET}  {BOLD}{color}● {significance:<10}{RESET}  "
            f"{GREY}{source_label:<22}{RESET}  {GREY}{timestamp}{RESET}"
        )
        out.append(f"{GREY}╠{thin}╣{RESET}")
        out.append(f"{GREY}║{RESET}  {BOLD}{title[:WIDTH-2]}{RESET}")
        for sl in summary_lines:
            out.append(f"{GREY}║{RESET}  {GREY}{sl}{RESET}")
        if url:
            out.append(f"{GREY}║{RESET}  {GREY}{url[:WIDTH-2]}{RESET}")
        out.append(f"{GREY}╚{bar}╝{RESET}")
        out.append("")
        return out

    def run(self, msg):
        msg = coerce_sink_message(msg)
        self.count += 1
        self.items.append(msg)

        if self.max_items and len(self.items) > self.max_items:
            self.items = self.items[-self.max_items:]

        if self._app_sse_enabled():
            self._emit_app_markdown(self._item_to_markdown(msg))
            return

        if self.max_items:
            # Situation Room mode — clear and redraw
            print(CLEAR, end="")
            now = datetime.now().strftime("%d %b %Y  %H:%M:%S")
            title = f" SITUATION ROOM  —  {now}  —  {self.count} items processed "
            print(f"{BOLD}{GREY}{'═' * WIDTH}{RESET}")
            print(f"{BOLD}{WHITE}{title.center(WIDTH)}{RESET}")
            print(f"{BOLD}{GREY}{'═' * WIDTH}{RESET}\n")
            for item in self.items:
                for line in self._format_item(item):
                    print(line)
        else:
            # Scrolling mode — append new item
            for line in self._format_item(msg):
                print(line)

    def finalize(self):
        if self._app_sse_enabled():
            self._emit_app_markdown(
                f"**Briefing complete** — _{self.count} item(s) processed._"
            )
            return
        print(f"\n{GREY}{'═' * (WIDTH+2)}{RESET}")
        print(f"  Briefing complete — {self.count} items filed.")
        print(f"{GREY}{'═' * (WIDTH+2)}{RESET}\n")
