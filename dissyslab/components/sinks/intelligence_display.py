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

    def _format_item(self, item):
        """Format one briefing item as a list of display lines."""
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
