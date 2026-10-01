# dissyslab/gallery/apps/paxos/roles/learner.py

"""
A learner of the Paxos algorithm.

DRAFT -- for review. The rule is the one in course/lecture_08.html:

    When an acceptor q changes its value it sends a message containing
    q.v to all learners. If a learner L has a null value and L receives
    messages from at least M acceptors, q, where all the messages have
    the same value of q.v, then L sets L.value = q.v.s.

So a learner counts messages, not acceptors in the abstract: it keeps
the latest pair it has heard from each acceptor, and learns as soon as
M of those pairs are the same pair. Once it has learned a value it
never changes it, which is the third requirement of the specification.

Ports
-----
``in_``   one message from each acceptor whenever that acceptor's value
          changes. Some of these are lost, which is why one learner can
          learn later than another, or not at all.
``out``   an announcement, once, when the value is learned:
          ``L0's out is console_printer``.

Message in
----------
    {"kind": "learn", "sender": "Q2", "v_s": "green", "v_t": (2, "P0")}

Message out
-----------
    {"learner": "L0", "value": "green", "at": (2, "P0"),
     "text": "L0 learned green, written in transaction (2, 'P0')"}
"""

from __future__ import annotations

from typing import Any, Dict, Tuple

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _names import bare  # noqa: E402

from dissyslab.core import Agent  # noqa: E402
from dissyslab.office.library import AgentRoleEntry  # noqa: E402


class _Learner(Agent):
    """One learner: hear M acceptors agree on one pair, then stop."""

    def __init__(
        self,
        name: str | None = None,
        majority: int = 3,
    ):
        super().__init__(
            name=name,
            inports=["in_"],
            outports=["out"],
        )
        self.M = int(majority)
        self.value: Any = None        # L.value
        self.at: Tuple[int, str] | None = None
        # the latest pair heard from each acceptor
        self.heard: Dict[str, Tuple[Any, Tuple[int, str]]] = {}

    @property
    def id(self) -> str:
        """``L0``: the name the office wrote. ``self.name`` is
        ``paxos::L0`` -- see ``_names.py``."""
        return bare(self.name)

    def run(self) -> None:
        while True:
            msg = self.recv("in_")
            if not isinstance(msg, dict) or msg.get("kind") != "learn":
                continue
            if self.value is not None:
                continue              # what a learner learns, it keeps
            sender, s, t = bare(msg.get("sender")), msg.get("v_s"), msg.get("v_t")
            if s is None or t is None:
                continue
            self.heard[sender] = (s, t)

            same = [q for q, pair in self.heard.items() if pair == (s, t)]
            if len(same) >= self.M:
                self.value, self.at = s, t
                self.send(
                    {
                        "learner": self.id,
                        "value":   self.value,
                        "at":      self.at,
                        "text": (
                            f"{self.id} learned {self.value}, written in "
                            f"transaction {self.at}"
                        ),
                    },
                    "out",
                )


role = AgentRoleEntry(
    name="learner",
    in_ports=("in_",),
    out_ports=("out",),
    factory=_Learner,
    names_own_ports=True,
)
