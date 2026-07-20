# dissyslab/gallery/apps/investment_club/roles/manager.py
"""
Manager — manager.

Single inbox, two message shapes to tell apart -- exactly OfficeSpeak's
own investment_club design (MANAGER's one inbox receives both JOIN's
paired recommendations and ACCOUNTANT's reply):

- a message with ``val_shares``/``oppo_shares`` -- the period's paired
  recommendation: combine into a proposed trade, ask the accountant
  (remembering the proposal in private state while waiting -- private,
  single-accessor memory, no gate needed for *this*).
- a message with ``fee`` -- the accountant's reply: finalize using the
  holdings the accountant already read, write the ledger, record the
  period's outcome, and tell the gate the period is done.

$100/share is a fixed, trivial price -- this fixture is about
validating record+gate sequencing, not modelling real markets.
"""

from __future__ import annotations

from typing import Any

from dissyslab.blocks.role import Role
from dissyslab.office.library import AgentRoleEntry

_PRICE_PER_SHARE = 100.0
_STATUSES = ["to_accountant", "to_ledger", "out", "done"]


def _make_manager_fn():
    pending: dict = {}

    def manager_fn(msg: Any):
        if "val_shares" in msg:
            period = msg["period"]
            proposed = msg["val_shares"] + msg["oppo_shares"]
            pending["period"] = period
            pending["proposed_shares"] = proposed
            print(
                f"[Manager] period {period}: proposing {proposed} shares "
                f"(val={msg['val_shares']}, oppo={msg['oppo_shares']}); "
                "asking accountant",
                flush=True,
            )
            return [
                ({"period": period, "proposed_shares": proposed}, "to_accountant")
            ]

        # An accountant reply.
        period = pending["period"]
        proposed = pending["proposed_shares"]
        cost = proposed * _PRICE_PER_SHARE
        new_shares = msg["current_shares"] + proposed
        new_cash = msg["current_cash"] - cost - msg["fee"]
        print(
            f"[Manager] period {period}: fee={msg['fee']:.2f}, "
            f"holdings before this trade: shares={msg['current_shares']}, "
            f"cash={msg['current_cash']:.2f} -> after: "
            f"shares={new_shares}, cash={new_cash:.2f}",
            flush=True,
        )
        return [
            (
                {"action": "write", "data": {"aapl_shares": new_shares, "cash": new_cash}},
                "to_ledger",
            ),
            (
                {
                    "period": period,
                    "bought": proposed,
                    "fee": msg["fee"],
                    "resulting_shares": new_shares,
                    "resulting_cash": new_cash,
                },
                "out",
            ),
            ({}, "done"),
        ]

    return manager_fn


role = AgentRoleEntry(
    name="manager",
    in_ports=("in_",),
    out_ports=tuple(_STATUSES),
    factory=lambda: Role(fn=_make_manager_fn(), statuses=list(_STATUSES)),
    description=(
        "Combine analyst recommendations, ask the accountant, finalize and "
        "write the ledger, signal the gate."
    ),
)
