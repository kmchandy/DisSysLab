# dissyslab/gallery/apps/recovery_demo/roles/pi_combiner.py

"""
Pi — pi_combiner.

Receives a mix of ``{"kind": "inside", ...}`` and
``{"kind": "outside", ...}`` messages on its single inport (the
compiler auto-inserts a MergeAsynch in front when fanin is needed,
which serializes the two streams onto one queue). Updates the
running inside/outside counts and emits a card with the current π
estimate after every received message.

State: two integer counters. ``save_state`` returns
``{"inside": int, "outside": int}``; ``load_state`` restores
both.
"""

from __future__ import annotations

from dissyslab.core import Agent
from dissyslab.office.library import AgentRoleEntry


class _PiCombiner(Agent):
    def __init__(self, name: str | None = None):
        super().__init__(name=name, inports=["in_"], outports=["out_"])
        self.inside: int = 0
        self.outside: int = 0

    def save_state(self):
        return {"inside": self.inside, "outside": self.outside}

    def load_state(self, state):
        if not isinstance(state, dict):
            return
        self.inside = int(state.get("inside", 0))
        self.outside = int(state.get("outside", 0))

    def _significance(self, total: int) -> str:
        if total >= 5000:
            return "HIGH"
        if total >= 500:
            return "MEDIUM"
        return "LOW"

    def run(self):
        while True:
            msg = self.recv("in_")
            kind = msg.get("kind")
            running = int(msg.get("running_count", 0))
            if kind == "inside":
                # Use the running_count from upstream rather than
                # incrementing locally — survives a recover where
                # upstream replays from a different cursor.
                self.inside = running
            elif kind == "outside":
                self.outside = running
            total = self.inside + self.outside
            if total > 0:
                pi_est = 4.0 * self.inside / total
                self.send(
                    {
                        "source":       "recovery_demo",
                        "title":        f"π ≈ {pi_est:.4f}",
                        "text":         (
                            f"Inside: {self.inside}   "
                            f"Outside: {self.outside}   "
                            f"Total: {total}"
                        ),
                        "significance": self._significance(total),
                    },
                    "out_",
                )


role = AgentRoleEntry(
    name="pi_combiner",
    in_ports=("in_",),
    out_ports=("out",),
    factory=_PiCombiner,
)
