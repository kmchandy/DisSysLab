# dissyslab/gallery/apps/investment_club/roles/oppo_analyst.py
"""
Oppo — oppo_analyst.

Trivial, deterministic stand-in for an emerging-opportunities
recommendation: reads a period-start signal (via Gate) and recommends
buying ``period * 3`` shares.
"""

from __future__ import annotations

from dissyslab.core import Agent
from dissyslab.office.library import AgentRoleEntry


class _OppoAnalyst(Agent):
    def __init__(self, name: str | None = None):
        super().__init__(name=name, inports=["in_"], outports=["out_"])

    def run(self) -> None:
        while True:
            msg = self.recv("in_")
            period = msg["period"]
            self.send({"period": period, "oppo_shares": period * 3}, "out_")


role = AgentRoleEntry(
    name="oppo_analyst",
    in_ports=("in_",),
    out_ports=("out",),
    factory=_OppoAnalyst,
    description="Emerging-opportunities recommendation: buy period*3 shares (trivial, deterministic).",
)
