# dissyslab/gallery/apps/investment_club/roles/val_analyst.py
"""
Val — val_analyst.

Trivial, deterministic stand-in for a value-investing recommendation:
reads a period-start signal (via Gate) and recommends buying
``period * 5`` shares -- enough variation across periods to make the
validation's holdings actually change period over period.
"""

from __future__ import annotations

from dissyslab.core import Agent
from dissyslab.office.library import AgentRoleEntry


class _ValAnalyst(Agent):
    def __init__(self, name: str | None = None):
        super().__init__(name=name, inports=["in_"], outports=["out_"])

    def run(self) -> None:
        while True:
            msg = self.recv("in_")
            period = msg["period"]
            self.send({"period": period, "val_shares": period * 5}, "out_")


role = AgentRoleEntry(
    name="val_analyst",
    in_ports=("in_",),
    out_ports=("out",),
    factory=_ValAnalyst,
    description="Value-investing recommendation: buy period*5 shares (trivial, deterministic).",
)
