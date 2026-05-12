# dissyslab/components/sinks/intelligence_display.py

"""
IntelligenceDisplay: Rich console sink for intelligence briefing offices.

Displays each briefing note as a color-coded bordered block.
In Situation Room mode (max_items set), refreshes the display in place
showing the last N items — like a live dashboard.
"""

from datetime import datetime
import json

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


def _as_display_str(value, max_len=None) -> str:
    """Coerce message fields to str for wrapping / slicing (handles nested dict/list)."""
    if value is None:
        s = ""
    elif isinstance(value, str):
        s = value
    elif isinstance(value, (dict, list)):
        s = json.dumps(value, ensure_ascii=False)
    else:
        s = str(value)
    if max_len is not None and len(s) > max_len:
        return s[:max_len]
    return s


def _try_parse_json_object(value):
    """If value is a str containing a JSON object, return the dict; else None."""
    if not isinstance(value, str):
        return None
    s = value.strip()
    if not s.startswith("{"):
        return None
    try:
        out = json.loads(s)
        return out if isinstance(out, dict) else None
    except json.JSONDecodeError:
        a, b = s.find("{"), s.rfind("}")
        if a == -1 or b <= a:
            return None
        try:
            out = json.loads(s[a : b + 1])
            return out if isinstance(out, dict) else None
        except json.JSONDecodeError:
            return None


def _wrap_to_width(text: str, width: int, max_lines: int) -> list[str]:
    """Split plain text into up to max_lines, each at most width chars (word-aware)."""
    words = text.split()
    line = ""
    lines = []
    for word in words:
        if len(line) + len(word) + 1 <= width:
            line += ("" if not line else " ") + word
        else:
            if line:
                lines.append(line)
            line = word
            if len(lines) >= max_lines:
                break
    if line and len(lines) < max_lines:
        lines.append(line)
    return lines[:max_lines]


def _job_style_summary(item: dict, inner_width: int):
    """
    If ``text`` is JSON from a matcher-style agent, show rating, resume fit, apply link.
    Returns (title, summary_lines) or None to fall back to generic formatting.
    """
    raw_text = item.get("text")
    blob = raw_text if isinstance(raw_text, dict) else None
    if blob is None and isinstance(raw_text, str):
        blob = _try_parse_json_object(raw_text)
    if not isinstance(blob, dict):
        return None

    title = _as_display_str(item.get("title") or blob.get("title") or "Listing")[:60]

    lines: list[str] = []
    company = blob.get("company")
    if company:
        lines.append(f"Company: {_as_display_str(company)[:inner_width]}")

    rating = blob.get("match_rating") or blob.get("rating") or blob.get("fit")
    if rating:
        lines.append(f"Match: {_as_display_str(rating)}")

    fit = (
        blob.get("matching_experiences")
        or blob.get("why_fit")
        or blob.get("relevance")
        or blob.get("resume_alignment")
        or blob.get("skills_match")
    )
    if isinstance(fit, list) and fit:
        fit_s = "; ".join(_as_display_str(x) for x in fit[:5])
        lines.extend(_wrap_to_width(f"Fit: {fit_s}", inner_width, 2))
    elif fit:
        lines.extend(_wrap_to_width(f"Fit: {_as_display_str(fit)}", inner_width, 2))

    apply_url = (
        _as_display_str(item.get("url", ""))
        or _as_display_str(blob.get("apply_url", ""))
        or _as_display_str(blob.get("application_url", ""))
        or _as_display_str(blob.get("link", ""))
        or _as_display_str(blob.get("job_url", ""))
        or _as_display_str(blob.get("url", ""))
    ).strip()
    if apply_url:
        lines.append(f"Apply: {apply_url[:inner_width]}")

    if not lines:
        return None

    return title, lines[:5]


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

    def _format_item(self, item):
        """Format one briefing item as a list of display lines."""
        significance = item.get("significance", "LOW")
        if isinstance(significance, str):
            significance = significance.upper()
        else:
            significance = str(significance).upper()

        raw_source = item.get("source", "unknown")
        source = _as_display_str(raw_source)[:40]
        inner = WIDTH - 4
        url = _as_display_str(item.get("url", ""))
        timestamp = _as_display_str(item.get("timestamp", ""))
        author = _as_display_str(item.get("author", ""))

        color = SIGNIFICANCE_COLOR.get(significance, WHITE)

        # Show @author for BlueSky, source name for RSS
        source_label = f"@{author[:15]}" if raw_source == "bluesky" else source[:20]

        job_fmt = _job_style_summary(item, inner)
        if job_fmt:
            title, summary_lines = job_fmt
        else:
            title_raw = item.get("title")
            title = (
                _as_display_str(title_raw)[:60]
                if title_raw not in (None, "")
                else _as_display_str(item.get("text", ""))[:60]
            )
            text = _as_display_str(item.get("text", ""))
            summary_lines = _wrap_to_width(text, inner, 3)

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
            out.append(f"{GREY}║{RESET}  {GREY}{sl[:WIDTH-2]}{RESET}")
        # Show top-level URL only if not already printed in structured block
        if url and not any(sl.strip().startswith("Apply:") for sl in summary_lines):
            out.append(f"{GREY}║{RESET}  {GREY}{url[:WIDTH-2]}{RESET}")
        out.append(f"{GREY}╚{bar}╝{RESET}")
        out.append("")
        return out

    def run(self, msg):
        self.count += 1
        self.items.append(msg)

        if self.max_items and len(self.items) > self.max_items:
            self.items = self.items[-self.max_items:]

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
        print(f"\n{GREY}{'═' * (WIDTH+2)}{RESET}")
        print(f"  Briefing complete — {self.count} items filed.")
        print(f"{GREY}{'═' * (WIDTH+2)}{RESET}\n")
