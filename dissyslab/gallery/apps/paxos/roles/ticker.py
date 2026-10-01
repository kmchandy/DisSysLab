# dissyslab/gallery/apps/paxos/roles/ticker.py

"""
A clock for the proposers.

DRAFT -- for review.

Sends ``{"kind": "tick"}`` to the proposers in turn, one tick every
``period`` seconds, ``ticks`` times in all. A tick is what starts a
transaction, so this agent decides how many transactions the office
executes and which proposer executes each one. Ticking one proposer at
a time keeps a demonstration readable; ticking them together is also a
legal computation, and a more interesting one.

Ports
-----
``in_``                  one message from a ``starter`` source.
``to_p0, to_p1, to_p2``  one outbox per proposer.
"""

from __future__ import annotations

import time

from dissyslab.core import Agent
from dissyslab.office.library import AgentRoleEntry


_OUT_PORTS = ("to_p0", "to_p1", "to_p2")

#: The office writes ``CLOCK's to_p0 is P0``; the runtime names the
#: outboxes by position, in the order above. See acceptor.py.
_RUNTIME = ["out_%d" % i for i in range(len(_OUT_PORTS))]


class _Ticker(Agent):
    """Tick the proposers in rotation."""

    def __init__(
        self,
        name: str | None = None,
        ticks: int = 6,
        period: float = 0.5,
    ):
        super().__init__(
            name=name,
            inports=["in_"],
            outports=list(_RUNTIME),
        )
        self.ticks = int(ticks)
        self.period = float(period)

    def run(self) -> None:
        self.recv("in_")                 # wait for the starter
        for i in range(self.ticks):
            self.send({"kind": "tick"}, _RUNTIME[i % len(_RUNTIME)])
            time.sleep(self.period)
        while True:
            # Out of ticks, but not out of the office: an agent whose
            # run() returns leaves its thread dead, and the shutdown
            # protocol then waits for an answer that never comes and
            # the office runs for ever. So wait here to be stopped,
            # which is what every other agent in this office is doing.
            self.recv("in_")


role = AgentRoleEntry(
    name="ticker",
    in_ports=("in_",),
    out_ports=_OUT_PORTS,
    factory=_Ticker,
)
