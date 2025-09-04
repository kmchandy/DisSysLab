from __future__ import annotations
from typing import Any, Dict, List, Optional
from datetime import datetime

from dsl.core import SimpleAgent
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text


class ConsoleFlushPrinter(SimpleAgent):
    """
    Pretty console sink for *flush* messages.

    Expected input messages (on inport 'in'):
        {"cmd": "flush", "payload": [...], "meta": {"title": "..."}}

    It prints a compact, colorful summary to the terminal:
      • Title (from meta['title'] or a default)
      • Total item count in the flush
      • Up to `sample_size` example rows (strings or dicts with key 'row')
      • Timestamp

    This is great for "cockpit" views where the console is the UI:
      upstream blocks → BatchOutput/Orchestrator → ConsoleFlushPrinter

    Notes for students
    ------------------
    - This is only a *viewer*. It doesn’t write to a file.
    - It reacts to messages immediately (no timers/sleeps).
    - It ignores any non-flush message politely (with a brief note).
    - On '__STOP__', it prints a small goodbye panel and returns.

    Parameters
    ----------
    sample_size : int
        How many example rows to show per flush (default 5).
    title_fallback : str
        Title used if meta['title'] is not provided.
    name : str
        Block name (shown in errors).
    """

    def __init__(
        self,
        *,
        sample_size: int = 5,
        title_fallback: str = "Digest",
        name: str = "ConsoleFlushPrinter",
    ) -> None:
        if sample_size <= 0:
            raise ValueError("sample_size must be >= 1")
        self.sample_size = sample_size
        self.title_fallback = title_fallback
        self._console = Console()

        # A viewer has one input and no outputs.
        super().__init__(name=name, inport="in", outports=[], handle_msg=self.handle_msg)

    # ----- helpers -----------------------------------------------------------

    @staticmethod
    def _row_text(item: Any) -> str:
        """Turn a payload item into a printable line."""
        if isinstance(item, str):
            return item
        if isinstance(item, dict):
            # Common convention in our examples
            if "row" in item:
                return str(item["row"])
            # Fallback: stringify dict
            return str(item)
        return str(item)

    # ----- behavior ----------------------------------------------------------

    def handle_msg(self, msg: Any, **_) -> None:
        # Stop path: small friendly panel
        if msg == "__STOP__":
            self._console.print(
                Panel.fit(
                    Text("Stopped console viewer.", style="bold"),
                    title="Console",
                    border_style="dim",
                )
            )
            return

        # Ignore unknown messages politely
        if not isinstance(msg, dict) or msg.get("cmd") != "flush":
            self._console.print(
                Panel.fit(
                    Text(
                        f"Ignored non-flush message: {type(msg).__name__}",
                        style="yellow",
                    ),
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

        # Build a pretty table of sample rows
        table = Table(expand=False, box=None,
                      show_header=False, padding=(0, 1))
        preview = payload[: self.sample_size]
        for item in preview:
            table.add_row("•", Text(self._row_text(item)))

        if total > self.sample_size:
            table.add_row(
                "",
                Text(f"... and {total - self.sample_size} more",
                     style="italic dim"),
            )

        header = Text.assemble(
            (title, "bold"),
            ("  "),
            (f"[{total} items]", "cyan"),
            ("  "),
            (timestamp, "dim"),
        )

        panel = Panel(
            table,
            title=header,
            border_style="cyan",
            padding=(1, 2),
        )
        self._console.print(panel)
