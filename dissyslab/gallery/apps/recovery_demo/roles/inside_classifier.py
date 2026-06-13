# dissyslab/gallery/apps/recovery_demo/roles/inside_classifier.py

"""
Alex — inside_classifier.

Receives one ``(x, y)`` point per message. If the point falls
inside the unit quarter-circle (``x² + y² < 1``), increments an
inside counter and emits a ``{"kind": "inside", "running_count": N}``
message. If the point is outside, emits nothing.

State: a single integer counter. ``save_state`` returns
``{"count": int}``; ``load_state`` restores it.
"""

from __future__ import annotations

from dissyslab.core import Agent
from dissyslab.office.library import AgentRoleEntry


class _InsideClassifier(Agent):
    def __init__(self, name: str | None = None):
        super().__init__(name=name, inports=["in_"], outports=["out_"])
        self.count: int = 0

    def save_state(self):
        return {"count": self.count}

    def load_state(self, state):
        self.count = int((state or {}).get("count", 0))

    def run(self):
        while True:
            msg = self.recv("in_")
            x = float(msg["x"])
            y = float(msg["y"])
            if x * x + y * y < 1.0:
                self.count += 1
                self.send(
                    {"kind": "inside", "running_count": self.count},
                    "out_",
                )


role = AgentRoleEntry(
    name="inside_classifier",
    in_ports=("in_",),
    out_ports=("out",),
    factory=_InsideClassifier,
)
