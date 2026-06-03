# dissyslab/gallery/apps/debate/sinks/debate_display.py

"""
DebateDisplay — situation_room-style console renderer for the debate
office.

Why this lives here
-------------------

The display hardcodes the debate office's schema: it knows about the
named panellists (``qwen``, ``gemma``, ``gpt``, ``claude``), the
moderator's ``send_to: continue|finish`` shape, and the per-problem
flow of "starter -> Sasha -> round 0 -> Sync -> Riley -> round 1 ->
...". That knowledge belongs to the debate app, not to the framework's
``components/sinks/``. Same convention as periodic_brief's app-local
sink lives in ``periodic_brief/sinks/``.

What it does
------------

The display subscribes to two upstream channels:

1. **Sync's ``out``** — the per-round merged dict containing every
   panellist's answer for that round. One message per round.
2. **Riley's ``continue`` and ``finish``** — the moderator's verdict
   for that round.

For each problem, it renders:

* A problem header (problem_id + the question text).
* For each round: one bordered card per panellist showing
  ``answer / confidence / reasoning``, then a moderator card with
  the moderator_note (for ``continue``) or the final verdict (for
  ``finish``).
* A trailer hinting at the step-through prompt that Sasha will
  print if ``DSL_DEBATE_STEP=1`` is set.

The display does **not** block on input — that's the gate role's
job. The display just renders messages as they arrive.

Distinguishing inbound messages
-------------------------------

The same sink receives three distinct shapes; we discriminate by
which fields are present:

* Sync output:    has top-level ``qwen`` / ``gemma`` / ``gpt`` /
                  ``claude`` keys (or whatever the office is using)
                  and no ``send_to``.
* Riley continue: has ``send_to == "continue"`` and ``history``.
                  The last history entry is this round's snapshot
                  including the moderator_note.
* Riley finish:   has ``send_to == "finish"`` and ``final_answer``.
"""

from __future__ import annotations

import os
from typing import Any, Dict

# ── ANSI colour codes (no extra dependency) ──────────────────────────

RED     = "\033[91m"
YELLOW  = "\033[93m"
GREEN   = "\033[92m"
BLUE    = "\033[94m"
MAGENTA = "\033[95m"
CYAN    = "\033[96m"
WHITE   = "\033[97m"
GREY    = "\033[90m"
BOLD    = "\033[1m"
DIM     = "\033[2m"
ITALIC  = "\033[3m"
UNDERLINE = "\033[4m"
RESET   = "\033[0m"

WIDTH = 70

# One colour per panellist so a glance shows which agent said what.
_PANELLIST_COLOURS = {
    "qwen":   CYAN,
    "gpt":    GREEN,
    "claude": YELLOW,
}

# Names the display recognises as panellists. Add more here if the
# office grows back to N=4+ agents — the sink picks up new keys
# automatically only if listed here. ``gemma`` was removed because
# Gemma 4 wouldn't follow the JSON output discipline; restore the
# entry alongside its colour if you bring Gemma back.
_PANELLIST_KEYS = ("qwen", "gpt", "claude")


def _wrap(text: str, max_lines: int = 4, width: int = WIDTH - 4) -> list[str]:
    """Wrap ``text`` to ``width`` columns, capped at ``max_lines``."""
    if not text:
        return []
    words = str(text).split()
    out: list[str] = []
    line = ""
    for word in words:
        if len(line) + len(word) + 1 <= width:
            line += ("" if not line else " ") + word
        else:
            out.append(line)
            line = word
            if len(out) >= max_lines:
                return out
    if line and len(out) < max_lines:
        out.append(line)
    return out


def _truncate(text: str, width: int = WIDTH - 4) -> str:
    s = str(text)
    return s if len(s) <= width else s[: width - 1] + "…"


def _as_str(value) -> str:
    """Coerce arbitrary field value to a string (None -> '')."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return str(value)


class DebateDisplay:
    """Sink that renders one debate panel's progression to the terminal.

    Args:
        show_reasoning: When True (default), each panellist card
            includes the panellist's reasoning. Set False for a
            terser "answers only" view.
        max_reasoning_lines: Cap reasoning at this many wrapped
            lines per panellist card. Default 4.
    """

    def __init__(
        self,
        show_reasoning: bool = True,
        max_reasoning_lines: int = 4,
    ):
        self.show_reasoning = show_reasoning
        self.max_reasoning_lines = max_reasoning_lines
        # Per-problem state: track the current problem_id and round so
        # the display can print a header on transitions.
        self._current_problem_id: str = ""

    # ── DisSysLab sink interface ──────────────────────────────────────

    def run(self, msg: Any) -> None:
        if not isinstance(msg, dict):
            return
        if msg.get("end_of_stream"):
            self._render_stream_end()
            return
        # Discriminate the three message shapes.
        if msg.get("send_to") == "finish":
            self._render_finish(msg)
        elif msg.get("send_to") == "continue":
            self._render_continue(msg)
        elif any(k in msg for k in _PANELLIST_KEYS):
            self._render_round(msg)
        # Anything else (e.g. an unrecognised dict) is silently
        # dropped; we don't want to spam the console with junk.

    # ── Rendering ─────────────────────────────────────────────────────

    def _maybe_render_problem_header(self, msg: Dict[str, Any]) -> None:
        problem_id = _as_str(msg.get("problem_id"))
        if problem_id == self._current_problem_id:
            return
        self._current_problem_id = problem_id
        problem = _as_str(msg.get("problem"))
        bar = "═" * WIDTH
        print()
        print(f"{BOLD}{WHITE}╔{bar}╗{RESET}")
        head = f"  Problem {problem_id or '?'}"
        pad = " " * max(0, WIDTH - len(head))
        print(f"{BOLD}{WHITE}║{head}{pad}║{RESET}")
        for line in _wrap(problem, max_lines=4):
            row = f"  {line}"
            row += " " * max(0, WIDTH - len(row))
            print(f"{BOLD}{WHITE}║{row}║{RESET}")
        print(f"{BOLD}{WHITE}╚{bar}╝{RESET}")

    def _render_round(self, msg: Dict[str, Any]) -> None:
        """Print one card per panellist, headed by 'Round N'."""
        self._maybe_render_problem_header(msg)
        round_no = msg.get("round", 0)
        print()
        print(f"  {BOLD}Round {round_no}{RESET}")
        for key in _PANELLIST_KEYS:
            answer_block = msg.get(key)
            if not isinstance(answer_block, dict):
                continue
            self._render_panellist_card(key, answer_block)

    def _render_panellist_card(self, name: str, block: Dict[str, Any]) -> None:
        colour = _PANELLIST_COLOURS.get(name, WHITE)
        answer = _truncate(_as_str(block.get("answer")), width=WIDTH - 18)
        try:
            confidence = float(block.get("confidence", 0.0))
        except (TypeError, ValueError):
            confidence = 0.0
        reasoning = _as_str(block.get("reasoning"))

        bar = "─" * WIDTH
        header = (
            f"  {colour}{BOLD}● {name:<7}{RESET}"
            f"  {GREY}conf {confidence:>4.2f}{RESET}"
            f"  {colour}answer: {answer}{RESET}"
        )
        print(f"  {GREY}┌{bar}┐{RESET}")
        print(header)
        if self.show_reasoning and reasoning:
            print(f"  {GREY}│{RESET}")
            for line in _wrap(reasoning, max_lines=self.max_reasoning_lines):
                # No DIM here — DIM is intentionally faint and was
                # unreadable on white terminals. Default foreground
                # colour reads as black on light themes and white on
                # dark themes.
                print(f"  {GREY}│{RESET}  {line}")
        print(f"  {GREY}└{bar}┘{RESET}")

    def _render_continue(self, msg: Dict[str, Any]) -> None:
        """Print the moderator's continue verdict for the just-completed
        round."""
        self._maybe_render_problem_header(msg)
        history = msg.get("history") or []
        latest = history[-1] if history else {}
        note = _as_str(
            latest.get("moderator_note") if isinstance(latest, dict) else ""
        )
        round_no = (
            latest.get("round") if isinstance(latest, dict) else None
        )
        bar = "─" * WIDTH
        print()
        rnd = f" (round {round_no})" if round_no is not None else ""
        print(
            f"  {BOLD}{BLUE}Riley → continue{rnd}{RESET}"
        )
        print(f"  {BLUE}┌{bar}┐{RESET}")
        if note:
            for line in _wrap(note, max_lines=4):
                print(f"  {BLUE}│{RESET}  {ITALIC}{line}{RESET}")
        else:
            print(f"  {BLUE}│{RESET}  {GREY}(no moderator note){RESET}")
        print(f"  {BLUE}└{bar}┘{RESET}")

    def _render_finish(self, msg: Dict[str, Any]) -> None:
        """Print Riley's final verdict for this problem."""
        self._maybe_render_problem_header(msg)
        final_answer = _as_str(msg.get("final_answer"))
        final_reasoning = _as_str(msg.get("final_reasoning"))
        agreement = _as_str(msg.get("agreement"))
        rounds_used = msg.get("rounds_used", "?")
        bar = "═" * WIDTH
        print()
        print(f"  {BOLD}{GREEN}Riley → finish{RESET}  "
              f"{GREY}({agreement}, {rounds_used} round(s)){RESET}")
        print(f"  {GREEN}╔{bar}╗{RESET}")
        for line in _wrap(f"answer: {final_answer}", max_lines=2):
            print(f"  {GREEN}║{RESET}  {BOLD}{line}{RESET}")
        if final_reasoning:
            print(f"  {GREEN}║{RESET}")
            for line in _wrap(final_reasoning, max_lines=4):
                print(f"  {GREEN}║{RESET}  {line}")
        print(f"  {GREEN}╚{bar}╝{RESET}")
        # Hint about the step-through prompt that Sasha will print
        # when DSL_DEBATE_STEP=1 is in effect.
        if os.environ.get("DSL_DEBATE_STEP", "").strip().lower() in (
            "1", "true", "yes"
        ):
            print(f"  {GREY}(Sasha will pause for Enter before the "
                  f"next problem.){RESET}")
        # Reset so the next problem prints its header even if it has
        # the same id (it shouldn't, but be defensive).
        self._current_problem_id = ""

    def _render_stream_end(self) -> None:
        bar = "═" * WIDTH
        print()
        print(f"{BOLD}{WHITE}{bar}{RESET}")
        print(f"  {BOLD}{WHITE}All problems complete.{RESET}")
        print(f"{BOLD}{WHITE}{bar}{RESET}")

    def finalize(self) -> None:
        # No-op: rendering happens incrementally as messages arrive.
        pass
