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
CYAN = "\033[96m"          # Bright cyan — used for URL rows so the
                           # link visually pops out of the grey body.
RESET = "\033[0m"
BOLD = "\033[1m"
UNDERLINE = "\033[4m"
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


def _as_str(value) -> str:
    """Coerce an arbitrary field value into a string for safe rendering.

    Sinks downstream of LLM agents occasionally receive nested-dict
    fields (e.g. ``{"text": {"role": "assistant", "content": "..."}}``)
    when an agent forwards a raw model response without unwrapping.
    Returning a string here lets the rest of the renderer rely on
    ``str`` semantics (slicing, ``splitlines``, ``startswith``).
    """
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float, bool)):
        return str(value)
    # For dicts / lists / anything exotic, fall back to JSON so the
    # console still shows *something* legible rather than a crash.
    try:
        return json.dumps(value, ensure_ascii=False)
    except (TypeError, ValueError):
        return str(value)


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

    # ── Custom-app SSE bridge (Nyasha's React UI reads this) ──────────

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

    # ── Console rendering ─────────────────────────────────────────────

    # Field names this sink recognises as the per-item "verdict" — the
    # value the colour-coded bar uses. Different rater roles write
    # different names (severity_classifier → "severity",
    # relevance_rater → "relevance", impact_rater → "impact", etc.).
    # Rather than force every role to write a specific magic field,
    # the sink looks at this ordered list and uses the first one
    # present. Add new entries when a new rater role appears whose
    # verdict you want the display to colour by.
    _VERDICT_FIELDS = (
        "significance",
        "severity",
        "impact",
        "relevance",
        "urgency",
    )

    @staticmethod
    def _wrap(text: str, max_lines: int = 2) -> list:
        """Wrap ``text`` to fit inside the bordered block, capped to
        ``max_lines`` lines. Returns an empty list for empty input.

        Splits on whitespace; truncates by dropping overflow rather
        than producing an ellipsis. Width target is WIDTH - 4 so the
        border characters and a leading two-space gutter fit.
        """
        if not text:
            return []
        words = text.split()
        line = ""
        out_lines = []
        for word in words:
            if len(line) + len(word) + 1 <= WIDTH - 4:
                line += ("" if not line else " ") + word
            else:
                out_lines.append(line)
                line = word
            if len(out_lines) == max_lines:
                break
        if line and len(out_lines) < max_lines:
            out_lines.append(line)
        return out_lines

    @staticmethod
    def _is_bulleted(text: str) -> bool:
        """True if ``text`` looks like a pre-formatted bullet block.

        Used to switch ``_format_item`` from "wrap to N lines" mode
        (good for prose abstracts like arxiv_radar) into "preserve
        each bullet on its own row" mode (needed by matcher-style
        roles whose output is a vertical list of Title / Company /
        Location / ... lines that must stay vertical to be readable).

        Recognised bullet prefixes: ``•``, ``::``, and lines that
        clearly look like ``key: value`` enumerations (e.g.
        ``Title: ...``) — small models often drop the bullet glyph
        entirely but keep the vertical key/value structure.
        """
        if not text:
            return False
        stripped = text.lstrip()
        if stripped.startswith("•") or stripped.startswith("::"):
            return True
        head = text[:600]
        if "\n•" in head or "\n::" in head:
            return True
        # Last-resort: at least two early lines look like Field: value
        # AND a recognised matcher field name is present. Cheap heuristic.
        early_lines = [ln.strip() for ln in head.splitlines() if ln.strip()][:8]
        keyword_hits = sum(
            1 for ln in early_lines
            if ":" in ln
            and ln.split(":", 1)[0].strip().lower() in {
                "title", "company", "location",
                "salary", "match", "match rating",
            }
        )
        return keyword_hits >= 2

    @staticmethod
    def _format_bullets(text: str, max_lines: int = 18) -> list:
        """Render a bullet body line-by-line, capped at ``max_lines``.

        Each non-empty line of ``text`` becomes one display row. Long
        lines are truncated to ``WIDTH - 4`` characters; paragraph
        breaks (blank lines) are preserved as blank rows so visually
        grouped sub-blocks (header / Resume Matches / Skills /
        Gaps / Apply) stay grouped.
        """
        if not text:
            return []
        out = []
        for raw_line in text.splitlines():
            line = raw_line.rstrip()
            if not line:
                if out and out[-1] != "":
                    out.append("")
                continue
            if len(line) > WIDTH - 4:
                line = line[: WIDTH - 4]
            out.append(line)
            if len(out) >= max_lines:
                break
        while out and out[-1] == "":
            out.pop()
        return out

    def _format_item(self, item):
        """Format one briefing item as a list of display lines.

        Looks for an enrichment-style ``author`` field and a verdict-
        style ``reason`` field (set by rater roles like
        ``relevance_rater`` or ``impact_rater``). When present, each
        appears on its own labelled line so a glance shows: verdict,
        title, who wrote it, what it's about, why the rater rated it
        that way, and where to find it.
        """
        # Normalise envelope shape (Nyasha — handles custom-app message
        # variants where the payload is wrapped under "data" / etc.).
        item = coerce_sink_message(item)
        # Multi-field verdict lookup so any rater role works without
        # coordinated field naming.
        significance = "LOW"
        for _field in self._VERDICT_FIELDS:
            v = item.get(_field)
            if v:
                significance = str(v).upper()
                break
        # All displayed fields are coerced to strings here so the
        # rendering code below can rely on ``str`` semantics. Upstream
        # agents occasionally hand us nested dicts (e.g. an LLM
        # returning ``{"text": {...}}`` instead of a string); without
        # this coercion ``item["text"][:60]`` raises KeyError on a
        # slice because dicts don't support slicing.
        source = _as_str(item.get("source", "unknown")) or "unknown"
        text_raw = _as_str(item.get("text", ""))
        title = _as_str(item.get("title", "")) or text_raw[:60]
        # Prefer the cleaner abstract field (set by rater roles) over
        # the raw text concatenation when both are present.
        body = _as_str(item.get("abstract")) or text_raw
        url = _as_str(item.get("url", ""))
        timestamp = _as_str(item.get("timestamp", ""))
        author = _as_str(item.get("author", ""))
        reason = _as_str(item.get("reason", ""))

        color = SIGNIFICANCE_COLOR.get(significance, WHITE)

        # Show @author for BlueSky, source name for RSS
        source_label = f"@{author[:15]}" if source == "bluesky" else source[:20]

        # Pre-formatted bullet bodies (e.g. matcher roles emitting
        # Title / Company / Location / ... on separate lines) get
        # rendered line-by-line; everything else gets word-wrapped.
        bulleted = self._is_bulleted(body)
        if bulleted:
            body_lines = self._format_bullets(body, max_lines=18)
        else:
            body_lines = self._wrap(body, max_lines=2)
        reason_lines = self._wrap(reason, max_lines=2)

        bar = "═" * WIDTH
        thin = "─" * WIDTH

        out = []
        out.append(f"{GREY}╔{bar}╗{RESET}")
        out.append(
            f"{GREY}║{RESET}  {BOLD}{color}● {significance:<10}{RESET}  "
            f"{GREY}{source_label:<22}{RESET}  {GREY}{timestamp}{RESET}"
        )
        out.append(f"{GREY}╠{thin}╣{RESET}")
        # Title row. Skip it when the bullet body already opens with a
        # "• Title: ..." line — repeating the same string is just noise.
        first_body = body_lines[0] if body_lines else ""
        title_in_body = bulleted and first_body.lstrip().lower().startswith(
            ("• title", "•title")
        )
        if title and not title_in_body:
            out.append(f"{GREY}║{RESET}  {BOLD}{title[:WIDTH-2]}{RESET}")
        # Authors line — skip for Bluesky (the source label already
        # shows the @handle) and for items with no author field.
        if author and source != "bluesky":
            author_str = ("by " + author)[:WIDTH - 4]
            out.append(f"{GREY}║{RESET}  {GREY}{author_str}{RESET}")
        # Body / abstract.
        for sl in body_lines:
            if sl == "":
                out.append(f"{GREY}║{RESET}")
            else:
                out.append(f"{GREY}║{RESET}  {GREY}{sl}{RESET}")
        # Verdict reasoning. Tinted in the verdict colour so the eye
        # follows from the ● bar at the top to the explanation here.
        if reason_lines:
            out.append(
                f"{GREY}║{RESET}  {color}Reason: {reason_lines[0]}{RESET}"
            )
            for rline in reason_lines[1:]:
                out.append(f"{GREY}║{RESET}          {color}{rline}{RESET}")
        # Skip the trailing URL row if the body already includes it
        # (matcher-style outputs put it inline on an "Apply:" line).
        # Cyan + underline reads as a hyperlink in every modern
        # terminal and contrasts cleanly with the grey body above.
        if url and url not in body:
            out.append(
                f"{GREY}║{RESET}  {CYAN}{UNDERLINE}{url[:WIDTH-2]}{RESET}"
            )
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
