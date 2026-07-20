# dissyslab/gallery/apps/investment_club/roles/period_feed.py
"""
Feed — period_feed.

Validation fixture for `record` + `gate`
(dissyslab.office.library.record_role / gate_role), mirroring
OfficeSpeak's start_gallery/investment_club.md, Case 2. Fires once on
the office's single `starter` kick, then emits a fixed sequence of
period-start signals and stops. `Gate` (fed from these) admits one
period at a time regardless of how quickly they're all sent -- see
dissyslab/blocks/gate.py.
"""

from __future__ import annotations

from dissyslab.core import Agent
from dissyslab.office.library import AgentRoleEntry

_NUM_PERIODS = 3


class _PeriodFeed(Agent):
    def __init__(self, name: str | None = None):
        super().__init__(name=name, inports=["in_"], outports=["out_"])

    def run(self) -> None:
        self.recv("in_")  # the starter's single kick
        for period in range(1, _NUM_PERIODS + 1):
            self.send({"period": period}, "out_")


role = AgentRoleEntry(
    name="period_feed",
    in_ports=("in_",),
    out_ports=("out",),
    factory=_PeriodFeed,
    description="Fire a fixed sequence of period-start signals once kicked by starter.",
)
