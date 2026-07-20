# dissyslab/gallery/apps/trading_room/roles/ledger.py
"""
Ledger — ledger.

A single-inbox keeper: approves or rejects one proposed trade at a
time and replies to whichever trader sent it. Because it reads one
proposal at a time from its single inbox and processes each
atomically, it needs no gate and no shared memory to stay consistent
— matching OfficeSpeak's own "What this example teaches" note for
``trading_room``. State (how many trades approved so far) is held in
a closure, per the framework's convention for stateful custom roles.

Trivial approval rule for this validation fixture: approve up to
``_LIMIT`` trades, reject anything after — enough to exercise both
outcomes without needing real positions/cash bookkeeping.
"""

from __future__ import annotations

from typing import Any

from dissyslab.blocks.role import Role
from dissyslab.office.library import AgentRoleEntry

_LIMIT = 2


def _make_ledger_fn():
    state = {"approved_count": 0}

    def ledger_fn(msg: Any):
        headline = msg.get("headline")
        if state["approved_count"] < _LIMIT:
            state["approved_count"] += 1
            print(
                f"[Ledger] approving trade on {headline!r} "
                f"(approved so far: {state['approved_count']})",
                flush=True,
            )
            return [({"headline": headline, "approved": True}, "reply_news")]
        print(f"[Ledger] rejecting trade on {headline!r} (limit reached)", flush=True)
        return [({"headline": headline, "approved": False}, "reply_news")]

    return ledger_fn


role = AgentRoleEntry(
    name="ledger",
    in_ports=("in_",),
    out_ports=("reply_news",),
    factory=lambda: Role(fn=_make_ledger_fn(), statuses=["reply_news"]),
    description="Approve up to a fixed limit of trades, one at a time, and reply.",
)
