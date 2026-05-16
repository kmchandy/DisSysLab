"""Synchronizer for periodic_brief_pro's news mini-pipeline.

Waits for one annotation on each of three named inports —
entity_extractor, topic_tagger, urgency_classifier — dict-merges
them, and emits the merged article on `out`.
"""
from dissyslab.core import Agent
from dissyslab.office_v2 import AgentRoleEntry


class _Synchronizer(Agent):
    def __init__(self, name=None):
        super().__init__(
            name=name,
            inports=["entity_extractor", "topic_tagger", "urgency_classifier"],
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
    in_ports=("entity_extractor", "topic_tagger", "urgency_classifier"),
    out_ports=("out",),
    factory=_Synchronizer,
    description=(
        "Wait for one message on each of three inports — "
        "entity_extractor, topic_tagger, urgency_classifier — "
        "dict-merge, emit on out."
    ),
)
