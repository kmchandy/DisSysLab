# live_alert_sink.py
# pip install rich

from __future__ import annotations
import json
import re
import atexit
from collections import deque
from typing import Deque
from rich.console import Console
from rich.live import Live
from rich.align import Align
from rich.markup import escape

# ---------- module-level state (persists across DSL calls) ----------
_console = Console()
_live: Live | None = None
_ring: Deque[str] = deque(maxlen=200)  # newest at top

# optional: fenced code blocks like ```json ... ```
_CODEFENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)


def _ensure_live_started() -> Live:
    global _live
    if _live is None:
        _live = Live(Align.left("Waiting for alerts..."),
                     console=_console, refresh_per_second=8, transient=False)
        _live.start()
        atexit.register(_stop_live)
    return _live


def _stop_live():
    global _live
    if _live is not None:
        try:
            _live.stop()
        except Exception:
            pass
        _live = None


def _parse_alert_json(s: str) -> dict:
    s = s.strip()
    m = _CODEFENCE_RE.search(s)
    if m:
        s = m.group(1)
    # Trim a single wrapping quote layer if present
    if (s.startswith("'") and s.endswith("'")) or (s.startswith('"') and s.endswith('"')):
        s = s[1:-1]
    data = json.loads(s)
    # Normalize expected keys
    keys = ["alert_type", "location", "issued_time",
            "start_time", "end_time", "headline", "short_advice"]
    return {k: (data.get(k) or "") for k in keys}


def _ensure_period(txt: str) -> str:
    txt = (txt or "").strip()
    return txt if not txt or txt.endswith((".", "!", "?")) else txt + "."


def _format_block(rec: dict) -> str:
    issued = rec["issued_time"] or ""
    a_type = rec["alert_type"] or ""
    loc = rec["location"] or ""
    headline = _ensure_period(rec["headline"])
    advice = _ensure_period(rec["short_advice"])

    a_type_col = f"[bold bright_red]{escape(a_type)}[/]"
    loc_col = f"[bright_blue]{escape(loc)}[/]"

    line1 = f"{issued}   {a_type_col}   {loc_col}"
    line2 = f"[bold yellow]WARNING:[/] {escape(headline)}"
    line3 = f"[bold green]ACTION:[/]  {escape(advice)}"
    return f"{line1}\n{line2}\n{line3}"


def _render_feed() -> str:
    return "\n\n".join(_ring)

# =======================
# DSL SINK (single string)
# =======================


def live_alert_sink(message: str) -> None:
    """
    DSL node: accept ONE message (str) each call.
    Message must be a JSON object with keys:
      alert_type, location, issued_time, start_time, end_time, headline, short_advice
    Side effect: keeps an updating console view alive.
    """
    live = _ensure_live_started()

    if message is None:
        return  # ignore

    try:
        rec = _parse_alert_json(message)
        block = _format_block(rec)
    except Exception as ex:
        # Show parse errors without killing the view
        _console.print(f"[red]Parse error:[/] {type(ex).__name__}: {ex}")
        return

    _ring.appendleft(block)
    live.update(Align.left(_render_feed()))

# (optional) DisSysLab-style wrapper if your DSL calls sink(agent, msg)


def live_alert_sink_node(agent, msg: str) -> None:
    live_alert_sink(msg)
