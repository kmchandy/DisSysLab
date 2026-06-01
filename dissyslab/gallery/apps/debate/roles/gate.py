# dissyslab/gallery/apps/debate/roles/gate.py

"""
Sasha — the gate role.

Sasha emits exactly one problem per inbound signal. The office wires
two upstream channels into Sasha:

1. The ``starter`` source fires once at startup → Sasha emits the
   first problem.
2. Riley's ``finish`` port fires after the four solvers have
   debated the current problem to convergence → Sasha emits the
   next problem.

This guarantees the four solvers only ever see one problem at a
time, even though they're connected in an iterative loop with Riley.

When the problems file is exhausted, Sasha emits one final message
with ``{"end_of_stream": true}`` and then stops. Downstream sinks
can use that as a shutdown signal; the framework also handles the
no-more-messages case cleanly on its own.

Problems file format (JSONL, one record per line)::

    {"id": "01", "problem": "What is 13 * 19?", "answer_key": "247"}
    {"id": "02", "problem": "Should the team adopt Rust?"}

Extra fields like ``answer_key`` pass through untouched, so the
moderator and the experimental harness can compare debate outputs
against ground truth without any extra wiring.

The file is looked up in this order:
1. ``problems.jsonl`` in the current working directory (so Jeffrey
   can swap problem banks without editing the office).
2. ``problems.jsonl`` next to this file (the office's default bank).
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from dissyslab.core import Agent
from dissyslab.office.library import AgentRoleEntry


_HERE = Path(__file__).resolve().parent
_DEFAULT_BANK = _HERE.parent / "problems.jsonl"


def _locate_problems() -> Path:
    cwd_candidate = Path.cwd() / "problems.jsonl"
    if cwd_candidate.is_file():
        return cwd_candidate
    if _DEFAULT_BANK.is_file():
        return _DEFAULT_BANK
    raise FileNotFoundError(
        "gate role: no problems.jsonl in the current directory and "
        f"no default bank at {_DEFAULT_BANK}. Create a problems.jsonl "
        "with one {\"problem\": \"...\"} record per line."
    )


def _load_bank(path: Path) -> list[dict]:
    items: list[dict] = []
    for ln in path.read_text(encoding="utf-8").splitlines():
        ln = ln.strip()
        if not ln or ln.startswith("#"):
            continue
        items.append(json.loads(ln))
    return items


def _step_through_enabled() -> bool:
    """True when the DSL_DEBATE_STEP env var asks for interactive
    step-through between problems.

    Recognised truthy values: ``"1"``, ``"true"``, ``"yes"`` (case-
    insensitive). Any other value, including unset, disables the
    pause and the office runs straight through the problem bank
    just like before.
    """
    return os.environ.get("DSL_DEBATE_STEP", "").strip().lower() in (
        "1", "true", "yes"
    )


class _Gate(Agent):
    """Emit one problem per inbound signal; end-of-stream when empty.

    When ``DSL_DEBATE_STEP=1`` is set in the environment, the gate
    blocks on standard input between problems (after the first), so
    the user can review the previous debate before the next one
    fires. Because every panellist downstream is waiting for this
    block to broadcast its next message, the pause naturally idles
    the whole pipeline — no other coordination is needed.
    """

    def __init__(self, name=None):
        super().__init__(
            name=name,
            inports=["in_"],
            outports=["out_"],
        )
        self._bank = _load_bank(_locate_problems())
        self._cursor = 0
        self._step = _step_through_enabled()

    def _pause_for_user(self) -> None:
        """Print a prompt and block on stdin. Best-effort: if stdin
        is closed or not a TTY (cron / CI / pipe), skip the pause
        so the office still runs straight through."""
        if not sys.stdin or not sys.stdin.isatty():
            return
        try:
            input("\n[Press Enter for the next problem...] ")
        except (EOFError, KeyboardInterrupt):
            # User EOF'd or Ctrl-C'd — treat as "fall through".
            print()

    def run(self) -> None:
        while True:
            _ = self.recv("in_")  # wait for starter, then Riley's finish
            if self._cursor >= len(self._bank):
                self.send({"end_of_stream": True}, "out_")
                return
            # Pause between problems (not before the first one).
            if self._step and self._cursor > 0:
                self._pause_for_user()
            item = self._bank[self._cursor]
            self._cursor += 1
            msg = {
                "problem": item.get("problem", item.get("text", "")),
                "problem_id": item.get("id", str(self._cursor)),
                "round": 0,
                "history": [],
            }
            for k, v in item.items():
                if k not in msg and k not in ("problem", "text"):
                    msg[k] = v
            self.send(msg, "out_")


role = AgentRoleEntry(
    name="gate",
    in_ports=("in_",),
    out_ports=("out",),
    factory=_Gate,
)
