# dissyslab/gallery/apps/paxos/roles/ticker.py

"""
An alarm clock for one proposer.

DRAFT -- for review.

Every proposer has its own ticker. A ticker sleeps, wakes its proposer
with ``{"kind": "tick"}``, and sleeps again, ``ticks`` times in all. A
tick is what starts a transaction, so a ticker decides how often its
proposer tries, and nothing in the algorithm depends on when.

How long it sleeps is a random variable: uniform on ``[T - delta,
T + delta]`` milliseconds, drawn again before every tick. Three
reasons it is random rather than fixed:

- fixed periods of equal length keep the proposers in lockstep, so the
  same interleaving repeats and the interesting ones never happen;
- real clocks drift, and an algorithm that needs them not to is not an
  asynchronous algorithm;
- two proposers that tick together keep superseding each other. With
  independent random waits they drift apart by themselves, which is
  the standard answer to that -- see the note on T below.

Choosing T, measured
--------------------
One transaction of this office -- a read to five acceptors, a majority
of replies, a write to five acceptors -- takes about 2 ms here, median,
and up to about 9 ms when a thread is unlucky. Thirty transactions,
ten at each of the three proposers, two runs at each T:

    T       transactions that reached a write
    2 ms     2, 4   of 30
    5 ms     8, 13
    20 ms   20, 12
    200 ms  21, 12

Two things to read off that. T of about 2 ms, the length of a
transaction, is too fast: almost nothing finishes. And raising T past
about 20 ms buys nothing, because what stops the rest is not overlap.
It is the numbering: each proposer numbers its transactions by its own
tick count, so all three arrive at the same number, the proposer name
breaks the tie, and the loser's requests are dropped by the acceptors
in silence. Per proposer at T = 200 ms, one run of each three:

    P0 1/10   P1 10/10   P2 10/10
    P0 2/10   P1  0/10   P2 10/10
    P0 6/10   P1  9/10   P2  4/10

A starved proposer is not a safety problem -- every one of those runs
reached agreement, and both learners learned the same value -- but a
class will ask about it, and the answer is the first open question in
this office's README, not T.

``delta`` matters less than ``T``; what it must not be is zero, which
keeps the proposers in lockstep. Two fifths of T, the default, is more
than enough to break it.

Ports
-----
``in_``   one message from a ``starter`` source, then nothing: the
          ticker waits here to be shut down after its last tick.
``out``   its proposer.
"""

from __future__ import annotations

import random
import time

from dissyslab.core import Agent
from dissyslab.office.library import AgentRoleEntry


#: One outbox, ``out``, wired to this ticker's own proposer.
_OUT_PORTS = ("out",)
_OUT = "out"


class _Ticker(Agent):
    """Wake one proposer, ``ticks`` times, at random intervals."""

    def __init__(
        self,
        name: str | None = None,
        ticks: int = 10,
        T: float = 5.0,
        delta: float = 2.0,
        seed: int | None = None,
    ):
        super().__init__(
            name=name,
            inports=["in_"],
            outports=[_OUT],
        )
        self.ticks = int(ticks)
        self.T = float(T)
        self.delta = float(delta)
        # Each ticker draws from its own stream. A seed fixes this
        # ticker's sequence of waits -- it does not make the run
        # repeatable, and three runs of this office with the same seeds
        # agreed on red at (1, 'P2'), blue at (6, 'P1') and red again:
        # the threads interleave differently every time.
        self.rnd = random.Random(seed)

    def wait_ms(self) -> float:
        """Milliseconds until the next alarm: uniform on T ± delta.

        Clamped at zero because a delta larger than T would otherwise
        ask for a negative wait, and `random.uniform` would happily
        return one.
        """
        lo = max(0.0, self.T - self.delta)
        hi = max(lo, self.T + self.delta)
        return self.rnd.uniform(lo, hi)

    def run(self) -> None:
        self.recv("in_")                 # wait for the starter
        for _ in range(self.ticks):
            time.sleep(self.wait_ms() / 1000.0)
            self.send({"kind": "tick"}, _OUT)
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
    names_own_ports=True,
)
