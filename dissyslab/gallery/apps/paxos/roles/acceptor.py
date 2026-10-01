# dissyslab/gallery/apps/paxos/roles/acceptor.py

"""
An acceptor of the Paxos algorithm.

DRAFT -- for review. The algorithm is the one in course/lecture_08.html.

An acceptor holds one variable, q.v, which is a pair

    q.v.s   a candidate consensus value, or None
    q.v.t   the id of the transaction that assigned q.v.s

and one more, q.t, the id of the transaction it is processing. A
transaction id is a pair ``(number, proposer name)``, so ids are unique
and totally ordered, and Python's tuple comparison is that order.

Ports
-----
``in_``           every request from every proposer arrives here.
``P0, P1, P2``    one outbox per proposer, each named after the
                  proposer it reaches: ``Q2's P1 is P1``. A request
                  carries the name of the proposer that sent it, so the
                  reply goes out on the outbox of that name --
                  ``self.send(reply, sender)``, and no table.
``learners``      one outbox, wired to both learners: ``Q2's learners
                  are L0 and L1``. Whenever q.v changes, the acceptor
                  tells every learner the pair it now holds -- the same
                  message to each, so one outbox is enough.

A reply is the one message in this office that is not a broadcast,
which is why the proposers get an outbox each and the learners do not.

Messages in
-----------
    {"kind": "read",  "sender": "P1", "t": (3, "P1")}
    {"kind": "write", "sender": "P1", "t": (3, "P1"), "s": "green"}

Messages out
------------
    {"kind": "reply", "sender": "Q2", "t": (3, "P1"),
     "v_s": "green", "v_t": (2, "P0")}          to one proposer
    {"kind": "learn", "sender": "Q2",
     "v_s": "green", "v_t": (3, "P1")}          to every learner

The reply carries the acceptor's own name, which is how a proposer
counts replies from M *different* acceptors.

The rules of the previous class are the first lines of the loop in
``run()``: a request from an earlier transaction is dropped, and any
other request moves the acceptor to the transaction that sent it.
"""

from __future__ import annotations

from typing import Any, Dict, Sequence

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _names import bare  # noqa: E402

from dissyslab.core import Agent  # noqa: E402
from dissyslab.office.library import AgentRoleEntry  # noqa: E402


#: Spelled out as a literal, and derived from rather than built up,
#: because ``dsl check`` reads this file instead of running it:
#: ``office/role_ports.py`` resolves a name bound to a literal and
#: nothing else, so ``_PROPOSERS + (_LEARNERS_PORT,)`` left it unable to
#: say what the acceptor's ports are -- which is a W15 on every acceptor
#: in the office, and a failing test.
_OUT_PORTS = ("P0", "P1", "P2", "learners")
_PROPOSERS = _OUT_PORTS[:3]
_LEARNERS_PORT = _OUT_PORTS[3]

_NO_ID = (0, "")          # smaller than every real transaction id


class _Acceptor(Agent):
    """One acceptor: reply to reads, obey writes, ignore the past."""

    def __init__(
        self,
        name: str | None = None,
        proposers: Sequence[str] = _PROPOSERS,
    ):
        super().__init__(
            name=name,
            inports=["in_"],
            outports=list(_OUT_PORTS),
        )
        # Each outbox is named after the proposer it reaches, so a
        # reply goes out on the outbox named after the proposer that
        # asked. There is no table to keep in step with anything.
        self.proposers = tuple(proposers)
        self.v_s: Any = None          # q.v.s
        self.v_t = _NO_ID             # q.v.t
        self.t = _NO_ID               # q.t

    @property
    def id(self) -> str:
        """``Q2``: the name the office wrote, and the id q puts in a
        message. ``self.name`` is ``paxos::Q2`` -- see ``_names.py``."""
        return bare(self.name)

    def run(self) -> None:
        while True:
            msg = self.recv("in_")
            if not isinstance(msg, dict):
                continue
            kind, t = msg.get("kind"), msg.get("t")
            sender = bare(msg.get("sender"))
            if kind not in ("read", "write") or t is None:
                continue
            if sender not in self.proposers:
                continue

            if t < self.t:
                # a request from an earlier transaction: treated as lost
                continue
            self.t = t                       # join the newer transaction

            if kind == "read":
                self.send(
                    {
                        "kind": "reply",
                        "sender": self.id,
                        "t":     self.t,
                        "v_s":   self.v_s,
                        "v_t":   self.v_t,
                    },
                    sender,
                )
            else:
                self.v_s, self.v_t = msg.get("s"), t
                # q.v has changed: one send, to every learner, because
                # every learner is told the same thing
                self.send(
                    {
                        "kind":   "learn",
                        "sender": self.id,
                        "v_s":    self.v_s,
                        "v_t":    self.v_t,
                    },
                    _LEARNERS_PORT,
                )


role = AgentRoleEntry(
    name="acceptor",
    in_ports=("in_",),
    out_ports=_OUT_PORTS,
    factory=_Acceptor,
    names_own_ports=True,
)
