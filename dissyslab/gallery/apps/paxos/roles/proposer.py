# dissyslab/gallery/apps/paxos/roles/proposer.py

"""
A proposer of the Paxos algorithm.

DRAFT -- for review. The algorithm is the one in course/lecture_08.html.

A proposer holds the value it would like the system to agree on,
``self.VALUE``, and has two things to do:

    a clock tick    start a transaction with a new id and send a read
                    request to every acceptor
    the M-th reply  compute f over the replies and send a write request
                    to every acceptor

A tick starts a transaction whether or not the previous one finished.
It has to: a transaction whose replies are lost never collects M of
them, and the next tick is its only retry. So two of a proposer's own
transactions can be in flight at once, and the one line that keeps
that safe is the test ``msg["t"] != self.t`` in ``run()``, which
discards an answer to a transaction this proposer has moved on from.

A transaction id is a pair ``(number, proposer name)``. The name makes
the ids of different proposers distinct even when the numbers collide,
and tuple comparison is the total order the proof needs.

Ports
-----
``in_``              clock ticks and replies both arrive here; a
                     proposer cannot afford to block on one kind while
                     the other is waiting.
``to_q0 ... to_q4``  one outbox per acceptor.

Messages in
-----------
    {"kind": "tick"}
    {"kind": "reply", "sender": "Q2", "t": (3, "P1"),
     "v_s": "green", "v_t": (2, "P0")}

Messages out
------------
    {"kind": "read",  "sender": "P1", "t": (3, "P1")}
    {"kind": "write", "sender": "P1", "t": (3, "P1"), "s": "green"}

``sender`` is the proposer's own name, which the acceptor uses to pick
the outbox it replies on. The ``sender`` of a reply is the acceptor's
name, which is how this agent counts replies from M different
acceptors: ``self.replies`` is keyed by acceptor name, so two replies
from one acceptor count once.
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _names import bare  # noqa: E402

from dissyslab.core import Agent  # noqa: E402
from dissyslab.office.library import AgentRoleEntry  # noqa: E402


_OUT_PORTS = ("to_q0", "to_q1", "to_q2", "to_q3", "to_q4")

#: The office writes ``P0's to_q0 is Q0``; the runtime names the
#: outboxes by position, in the order above. See acceptor.py.
_RUNTIME = ["out_%d" % i for i in range(len(_OUT_PORTS))]

_NO_ID = (0, "")


class _Proposer(Agent):
    """One proposer: read a majority, compute f, write every acceptor."""

    def __init__(
        self,
        name: str | None = None,
        value: Any = None,
        majority: int = 3,
    ):
        super().__init__(
            name=name,
            inports=["in_"],
            outports=list(_RUNTIME),
        )
        self.VALUE = value            # p.VALUE: what p proposes
        self.M = int(majority)
        self.number = 0               # the number half of the next id
        self.t = _NO_ID               # p.t: the transaction p is executing
        self.replies: Dict[str, Tuple[Any, Tuple[int, str]]] = {}

    @property
    def id(self) -> str:
        """``P0``: the name the office wrote, and the id p puts in a
        message. ``self.name`` is ``paxos::P0`` -- see ``_names.py``."""
        return bare(self.name)

    # ── f, as in the lecture ─────────────────────────────────────────
    def f(self, values: List[Tuple[Any, Tuple[int, str]]]) -> Any:
        """The value to write, given the replies of a majority."""
        if all(s is None for s, _ in values):
            # no acceptor holds a candidate: propose this proposer's value
            return self.VALUE
        # otherwise the candidate value that was assigned most recently
        # among the acceptors that were read: the s with the largest t
        t_max = max(t for _, t in values)
        return next(s for s, t in values if t == t_max)

    def run(self) -> None:
        while True:
            msg = self.recv("in_")
            if not isinstance(msg, dict):
                continue
            kind = msg.get("kind")

            if kind == "tick":
                # create new transaction, with an id larger than any this
                # proposer has used
                self.number += 1
                self.t = (self.number, self.id)
                self.replies = {}
                for port in self.outports:
                    self.send(
                        {"kind": "read", "sender": self.id, "t": self.t},
                        port,
                    )

            elif kind == "reply":
                # An acceptor replies with the id of the request it is
                # answering, so msg["t"] is always an id *this* proposer
                # made, and nothing in a reply is ever numbered above
                # self.number: a reply proves the read was not dropped,
                # so q.t <= msg["t"], and q.v.t <= q.t.
                if msg.get("t") != self.t:
                    # the one reply left to discard: an answer to an
                    # earlier transaction of this proposer, overtaken by
                    # the tick that started the current one. Counting it
                    # would mix two read sets.
                    continue
                sender = msg.get("sender")
                if sender is None:
                    continue
                self.replies[sender] = (msg.get("v_s"), msg.get("v_t"))
                if len(self.replies) == self.M:
                    # the M-th reply completes the read set R
                    d = self.f(list(self.replies.values()))
                    for port in self.outports:
                        self.send(
                            {
                                "kind":   "write",
                                "sender": self.id,
                                "t":      self.t,
                                "s":      d,
                            },
                            port,
                        )


role = AgentRoleEntry(
    name="proposer",
    in_ports=("in_",),
    out_ports=_OUT_PORTS,
    factory=_Proposer,
)
