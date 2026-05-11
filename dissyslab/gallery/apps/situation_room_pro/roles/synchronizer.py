"""Office-specific synchronizer for the situation_room capstone.

Sasha forks each unique article into four parallel branches — Eve
(entities), Sam (severity), Tom (topic), Greta (location). Each
branch adds exactly one new field and preserves the rest. Sync waits
for one message on each of its four named inports, dict-merges the
four messages into a single article carrying every enrichment, and
emits the merged article on ``out``.

The merge is order-independent because each upstream extractor
preserves the original article fields and only adds its own new key.
A simple ``dict.update`` therefore produces a clean union.

This role is intentionally office-specific. The four inport names
match the four extractors in ``office.md``. A more general
"synchronizer" with configurable inports could live in the
framework's library; for the capstone we keep it explicit.
"""
from dissyslab.core import Agent
from dissyslab.office_v2 import AgentRoleEntry


class _SituationRoomSynchronizer(Agent):
    """Wait for one msg on each of four inports; dict-merge; emit."""

    def __init__(self, name=None):
        super().__init__(
            name=name,
            inports=["entities", "severity", "topic", "location"],
            outports=["out_"],
        )

    def run(self) -> None:
        while True:
            merged: dict = {}
            for inport in self.inports:
                msg = self.recv(inport)
                if isinstance(msg, dict):
                    merged.update(msg)
            self.send(merged, "out_")


role = AgentRoleEntry(
    name="synchronizer",
    in_ports=("entities", "severity", "topic", "location"),
    out_ports=("out",),
    factory=_SituationRoomSynchronizer,
    description=(
        "Wait for one message on each of four inports — entities, "
        "severity, topic, location — dict-merge the four messages, "
        "emit the merged article on 'out'."
    ),
)
