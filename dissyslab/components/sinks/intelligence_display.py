# dissyslab/components/sinks/intelligence_display.py

"""
IntelligenceDisplay: Rich console sink for intelligence briefing offices.

Displays each briefing note as a color-coded bordered block.
In Situation Room mode (max_items set), refreshes the display in place
showing the last N items — like a live dashboard.
"""

from datetime import datetime

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

    def _format_item(self, item):
        """Format one briefing item as a list of display lines.

        Looks for an enrichment-style ``author`` field and a verdict-
        style ``reason`` field (set by rater roles like
        ``relevance_rater`` or ``impact_rater``). When present, each
        appears on its own labelled line so a glance shows: verdict,
        title, who wrote it, what it's about, why the rater rated it
        that way, and where to find it.
        """
        significance = "LOW"
        for _field in self._VERDICT_FIELDS:
            v = item.get(_field)
            if v:
                significance = str(v).upper()
                break
        source = item.get("source", "unknown")
        title = item.get("title", item.get("text", "")[:60])
        # Prefer the cleaner abstract field (set by rater roles) over
        # the raw text concatenation when both are present.
        body = item.get("abstract") or item.get("text", "")
        url = item.get("url", "")
        timestamp = item.get("timestamp", "")
        author = item.get("author", "")
        reason = item.get("reason", "")

        color = SIGNIFICANCE_COLOR.get(significance, WHITE)

        # Show @author for BlueSky, source name for RSS
        source_label = f"@{author[:15]}" if source == "bluesky" else source[:20]

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
        out.append(f"{GREY}║{RESET}  {BOLD}{title[:WIDTH-2]}{RESET}")
        # Authors line — skip for Bluesky (the source label already
        # shows the @handle) and for items with no author field.
        if author and source != "bluesky":
            author_str = ("by " + author)[:WIDTH - 4]
            out.append(f"{GREY}║{RESET}  {GREY}{author_str}{RESET}")
        # Body / abstract.
        for sl in body_lines:
            out.append(f"{GREY}║{RESET}  {GREY}{sl}{RESET}")
        # Verdict reasoning. Tinted in the verdict colour so the eye
        # follows from the ● bar at the top to the explanation here.
        if reason_lines:
            out.append(
                f"{GREY}║{RESET}  {color}Reason: {reason_lines[0]}{RESET}"
            )
            for rline in reason_lines[1:]:
                out.append(f"{GREY}║{RESET}          {color}{rline}{RESET}")
        if url:
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
