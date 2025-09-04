from __future__ import annotations
from typing import Any, Dict, List, Optional
from datetime import datetime

from dsl.core import SimpleAgent
from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text


class ConsolePrettyPrinter(SimpleAgent):
    """
    Pretty multi-line console viewer for *flush* messages.

    Expects messages like:
        {"cmd": "flush", "payload": [ ...rows... ], "meta": {"title": "..."}}

    Each row is shown as:
      • <title>                (bold bright_cyan)
        <link>                 (blue underline)
        <meta>                 (dim)     e.g., "espn.com • 2h ago"

    If a row is:
      - a dict with {"row": {"title": ..., "link": ..., "meta": ...}}, it uses those fields.
      - a dict with {"row": "<string>"} or a plain string, it shows it as a simple one-line fallback.

    Parameters
    ----------
    sample_size : int
        How many rows to preview per flush (default 6).
    title_fallback : str
        Used when meta['title'] is missing.
    name : str
        Block name.
    """

    def __init__(
        self,
        *,
        sample_size: int = 6,
        title_fallback: str = "Digest",
        name: str = "ConsolePrettyPrinter",
    ) -> None:
        if sample_size <= 0:
            raise ValueError("sample_size must be >= 1")
        self.sample_size = sample_size
        self.title_fallback = title_fallback
        self._console = Console()
        super().__init__(name=name, inport="in", outports=[], handle_msg=self.handle_msg)

    # ---- helpers ------------------------------------------------------------

    @staticmethod
    def _structured_from(item: Any) -> Dict[str, Optional[str]] | None:
        """
        Try to extract {"title", "link", "meta"} from item.
        Understands:
          {"row": {"title": "...", "link": "...", "meta": "..."}}
        """
        if isinstance(item, dict):
            row = item.get("row")
            if isinstance(row, dict):
                t = row.get("title")
                l = row.get("link")
                m = row.get("meta")
                if any([t, l, m]):
                    return {"title": t, "link": l, "meta": m}
        return None

    @staticmethod
    def _fallback_text(item: Any) -> Text:
        """Fallback: render item (or item['row']) as a single line of text."""
        if isinstance(item, dict) and "row" in item and not isinstance(item["row"], dict):
            return Text(str(item["row"]))
        return Text(str(item))

    def _format_group(self, item: Any) -> Group:
        """
        Build a 3-line Rich Group for a structured row,
        or a 1-line fallback if it's not structured.
        """
        s = self._structured_from(item)
        if not s:
            return Group(self._fallback_text(item))

        bullet = Text("• ", style="white")
        title = Text(str(s.get("title") or "Untitled"),
                     style="bold bright_cyan")
        line1 = Text.assemble(bullet, title)

        link = s.get("link") or ""
        line2 = Text(str(link), style="blue underline")

        meta = s.get("meta") or ""
        line3 = Text(str(meta), style="dim")

        return Group(line1, line2, line3)

    # ---- behavior -----------------------------------------------------------

    def handle_msg(self, msg: Any, **_) -> None:
        if msg == "__STOP__":
            self._console.print(
                Panel.fit(Text("Stopped console viewer.", style="bold"),
                          title="Console", border_style="dim")
            )
            return

        if not isinstance(msg, dict) or msg.get("cmd") != "flush":
            self._console.print(
                Panel.fit(
                    Text(
                        f"Ignored non-flush message: {type(msg).__name__}", style="yellow"),
                    title="Console",
                    border_style="yellow",
                )
            )
            return

        payload: List[Any] = msg.get("payload", []) or []
        meta: Dict[str, Any] = msg.get("meta", {}) or {}
        title = str(meta.get("title", self.title_fallback))
        total = len(payload)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        table = Table(expand=False, box=None,
                      show_header=False, padding=(0, 1))
        for item in (payload[: self.sample_size]):
            table.add_row(self._format_group(item))

        if total > self.sample_size:
            table.add_row(
                Text(f"... and {total - self.sample_size} more", style="italic dim"))

        header = Text.assemble(
            (title, "bold"),
            ("  "),
            (f"[{total} items]", "cyan"),
            ("  "),
            (timestamp, "dim"),
        )

        panel = Panel(table, title=header,
                      border_style="magenta", padding=(1, 2))
        self._console.print(panel)
