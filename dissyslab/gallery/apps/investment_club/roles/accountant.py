# dissyslab/gallery/apps/investment_club/roles/accountant.py
"""
Accountant — accountant.

The corrected version from OfficeSpeak's own worked example
(start_gallery/investment_club.md, "The famous correction"): before
pricing a proposed trade, ask the ledger for the *current* holdings
and wait for them -- taxes/fees depend on what the club currently
holds, not just the proposed move. Single inbox, two message shapes
to tell apart: the manager's proposal, and the ledger's reply to this
accountant's own read.

Fee here is a trivial, deterministic stand-in ($1/share traded plus
0.1% of the *current* position's value) -- picked specifically because
it depends on the ledger read, so a wrong read (stale, or leaking a
different period's holdings) would show up as a wrong fee.
"""

from __future__ import annotations

from typing import Any

from dissyslab.blocks.role import Role
from dissyslab.office.library import AgentRoleEntry

_PRICE_PER_SHARE = 100.0
_STATUSES = ["to_ledger", "to_manager"]


def _make_accountant_fn():
    pending: dict = {}

    def accountant_fn(msg: Any):
        if "proposed_shares" in msg:
            pending["period"] = msg["period"]
            pending["proposed_shares"] = msg["proposed_shares"]
            print(
                f"[Accountant] period {msg['period']}: asking ledger for "
                "current holdings before pricing",
                flush=True,
            )
            return [({"action": "read"}, "to_ledger")]

        # The ledger's reply to this accountant's own read.
        current_shares = msg["aapl_shares"]
        current_cash = msg["cash"]
        proposed = pending["proposed_shares"]
        fee = 1.0 * proposed + 0.001 * current_shares * _PRICE_PER_SHARE
        print(
            f"[Accountant] period {pending['period']}: current holdings "
            f"shares={current_shares}, cash={current_cash:.2f} -> fee={fee:.2f}",
            flush=True,
        )
        return [
            (
                {
                    "fee": fee,
                    "current_shares": current_shares,
                    "current_cash": current_cash,
                },
                "to_manager",
            )
        ]

    return accountant_fn


role = AgentRoleEntry(
    name="accountant",
    in_ports=("in_",),
    out_ports=tuple(_STATUSES),
    factory=lambda: Role(fn=_make_accountant_fn(), statuses=list(_STATUSES)),
    description="Read current holdings from the ledger before pricing a proposed trade.",
)
