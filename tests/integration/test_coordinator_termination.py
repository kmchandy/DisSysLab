"""Regression test for #47 — termination detection with a coordinator that
is left blocked on an inport whose channel is empty while ANOTHER of its
inports still holds an unreachable, buffered message.

Office:

    SRC0 (2 items) ──in_0──▶ JOIN (merge_synch) ──out_──▶ OUT (sink)
    SRC1 (3 items) ──in_1──▶ JOIN

merge_synch pairs (a0,b0) and (a1,b1), emitting two joined messages. SRC1's
third item is left buffered in in_1. JOIN then blocks on in_0 (its next
round's first slot), whose source SRC0 has exhausted. No further output is
possible, yet the SRC1→in_1 channel is nonempty.

Before the fix, os_agent required *every* edge balanced (sent==received),
so the leftover on in_1 made it wait forever → the office hung.
After the fix, JOIN reports waiting_on="in_0"; os_agent disregards the
nonempty in_1 channel (JOIN is not reading it) and terminates.

If this test hangs, the bug is back.
"""
from __future__ import annotations

from dissyslab.network import Network
from dissyslab.blocks.source import Source
from dissyslab.blocks.sink import Sink
from dissyslab.blocks.merge_synch import MergeSynch
from dissyslab.blocks.gate import Gate


class Feed:
    """A tiny exhaustible source body: emits its list, then None."""
    def __init__(self, data):
        self.data = list(data)
        self.i = 0

    def run(self):
        if self.i >= len(self.data):
            return None
        v = self.data[self.i]
        self.i += 1
        return v


def build_uneven_join():
    joined = []
    net = Network(
        name="uneven_join",
        blocks={
            "SRC0": Source(fn=Feed(["a0", "a1"]).run, name="SRC0", interval=0.01),
            "SRC1": Source(fn=Feed(["b0", "b1", "b2"]).run, name="SRC1", interval=0.01),
            "JOIN": MergeSynch(inports=["in_0", "in_1"], name="JOIN"),
            "OUT":  Sink(fn=joined.append, name="OUT"),
        },
        connections=[
            ("SRC0", "out_", "JOIN", "in_0"),
            ("SRC1", "out_", "JOIN", "in_1"),
            ("JOIN", "out_", "OUT",  "in_"),
        ],
    )
    net._joined = joined
    return net


def test_coordinator_with_unpaired_leftover_terminates():
    net = build_uneven_join()
    # If #47 regresses, run_network never returns and the test-runner
    # timeout fires. On success it returns promptly.
    net.run_network()
    # Exactly the two pairs were emitted; the leftover b2 was never joined.
    assert net._joined == [["a0", "b0"], ["a1", "b1"]], net._joined


def build_starved_gate():
    """A gate left blocked on its `done` inport while `in_` still holds a
    buffered item.

        DATA (3 items) ──in_──▶ GATE ──out_──▶ OUT (sink)
        DONE (1 item)  ─done──▶ GATE

    GATE admits d0 (busy), reads the single `done` (idle), admits d1
    (busy), then blocks on `done` — but DONE is exhausted. d2 sits
    unread in `in_`. waiting_on="done", so os_agent disregards the
    nonempty `in_` channel and terminates.
    """
    admitted = []
    net = Network(
        name="starved_gate",
        blocks={
            "DATA": Source(fn=Feed(["d0", "d1", "d2"]).run, name="DATA", interval=0.01),
            "DONE": Source(fn=Feed(["ok"]).run, name="DONE", interval=0.05),
            "GATE": Gate(name="GATE"),
            "OUT":  Sink(fn=admitted.append, name="OUT"),
        },
        connections=[
            ("DATA", "out_", "GATE", "in_"),
            ("DONE", "out_", "GATE", "done"),
            ("GATE", "out_", "OUT",  "in_"),
        ],
    )
    net._admitted = admitted
    return net


def test_gate_blocked_on_control_terminates():
    net = build_starved_gate()
    net.run_network()          # hangs here if #47 regresses
    # d0 and d1 were admitted; d2 stayed unread behind the closed gate.
    assert net._admitted == ["d0", "d1"], net._admitted


if __name__ == "__main__":
    net = build_uneven_join()
    net.run_network()
    print("merge_synch: terminated cleanly.")
    print("  joined output:", net._joined)
    print("  leftover 'b2' correctly left unpaired on in_1 (office still stopped).")

    net = build_starved_gate()
    net.run_network()
    print("gate: terminated cleanly.")
    print("  admitted:", net._admitted)
    print("  d2 correctly left unread behind the closed gate (office still stopped).")
