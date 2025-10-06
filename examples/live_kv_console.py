# live_kv_sink.py
# pip install rich

from __future__ import annotations
import json
from collections import deque
from typing import Any, Deque, Dict, Iterator, List, Sequence

from rich.console import Console
from rich.live import Live
from rich.align import Align
from rich.markup import escape

console = Console()

# ---------- formatting ----------


def _format_value(v: Any) -> List[str]:
    """Return a list of lines for a value."""
    if v is None:
        return ["null"]
    if isinstance(v, (str, int, float, bool)):
        return [escape(str(v))]
    if isinstance(v, list):
        lines: List[str] = []
        for itm in v:
            if isinstance(itm, (dict, list)):
                lines.append(
                    "- " + escape(json.dumps(itm, ensure_ascii=False)))
            else:
                lines.append("- " + escape(str(itm)))
        return lines or ["[]"]
    if isinstance(v, dict):
        pretty = json.dumps(v, ensure_ascii=False)
        return [escape(pretty)]
    return [escape(repr(v))]


def _order_keys(d: Dict[str, Any], prefer: Sequence[str] = ("title", "organizations", "science_terms")) -> List[str]:
    """Place preferred keys first, then the rest in stable/alphabetical order."""
    keys = list(d.keys())
    ordered = [k for k in prefer if k in d]
    for k in sorted(keys):
        if k not in ordered:
            ordered.append(k)
    return ordered


def _format_block(rec: Dict[str, Any]) -> str:
    """Build a text block: each key on one line, its value(s) on the next line(s)."""
    lines: List[str] = []
    lines.append("-" * 40)   # ASCII bar; tweak length if you like
    lines.append("")          # extra blank line
    for k in _order_keys(rec):
        lines.append(f"[bold]{escape(k)}[/]")      # key line
        lines.extend(_format_value(rec.get(k)))    # value lines
        lines.append("")                           # blank between key groups
    if lines and lines[-1] == "":
        lines.pop()
    return "\n".join(lines)


def _render_feed(blocks) -> str:
    # Separate records by a single blank line
    return "\n\n".join(blocks)

# ---------- stream mode (iterator of dicts) ----------


def live_print_kv(messages: Iterator[Dict[str, Any]], *, max_records: int = 200, refresh_per_second: int = 8) -> None:
    """
    Live console viewer for a stream of dict messages.
    Each dict can have any keys. For arrays, prints one item per line.
    The view updates as new messages arrive; newest appears at the top.
    """
    ring: Deque[str] = deque(maxlen=max_records)
    with Live(Align.left("Waiting for messages..."), console=console, refresh_per_second=refresh_per_second, transient=False) as live:
        for rec in messages:
            try:
                block = _format_block(rec)
            except Exception as ex:
                console.print(
                    f"[red]Format error:[/] {type(ex).__name__}: {ex}")
                continue
            ring.appendleft(block)
            live.update(Align.left(_render_feed(ring)))

# ---------- DSL sink mode (one dict per call) ----------


_live: Live | None = None
_ring: Deque[str] = deque(maxlen=200)


def kv_live_sink(message: Dict[str, Any]) -> None:
    """
    DSL-friendly sink: call once per dict message.
    Keeps the console open and appends each record.
    """
    global _live
    if _live is None:
        _live = Live(Align.left("Waiting for messages..."),
                     console=console, refresh_per_second=8, transient=False)
        _live.start()

    try:
        block = _format_block(message)
    except Exception as ex:
        console.print(f"[red]Format error:[/] {type(ex).__name__}: {ex}")
        return

    _ring.appendleft(block)
    _live.update(Align.left(_render_feed(_ring)))
