# dsl/blocks/merge_synch.py
"""
Merge Agents: Combine multiple inputs into single output.

MergeSynch: Synchronous merge in round-robin order (use sparingly).
For most use cases, prefer MergeAsynch in fanin.py.

Termination is signaled by os_agent via _Shutdown, handled transparently
by recv(). No explicit STOP handling needed.
"""

from __future__ import annotations
from typing import Optional

from dsl.core import Agent


class MergeSynch(Agent):
    """
    MergeSynch agent: synchronously combines multiple inputs in round-robin order.

    **WARNING: Use only when deterministic ordering is required AND all inputs
    produce messages at similar rates. For most use cases, prefer MergeAsynch.**

    **Ports:**
    - Inports: ["in_0", "in_1", ..., "in_{n-1}"]
    - Outports: ["out_"]

    **Termination:**
    Termination is detected by os_agent and signaled via _Shutdown,
    which recv() handles transparently by raising _ShutdownSignal.
    """

    def __init__(self, *, num_inputs: int, name: Optional[str] = None):
        if num_inputs < 1:
            raise ValueError(
                f"MergeSynch requires at least 1 input, got {num_inputs}"
            )

        inports = [f"in_{i}" for i in range(num_inputs)]
        super().__init__(name=name, inports=inports, outports=["out_"])
        self.num_inputs = num_inputs

    @property
    def default_inport(self) -> Optional[str]:
        """No default input (multiple inputs - ambiguous)."""
        return None

    @property
    def default_outport(self) -> str:
        """Default output port for edge syntax."""
        return "out_"

    def run(self) -> None:
        """
        Synchronous merge loop: collect batches in round-robin order.

        Collects one message from each input in order, sends as a list.
        recv() intercepts _Shutdown and raises _ShutdownSignal,
        which unwinds this loop cleanly.
        """
        while True:
            batch = []
            for inport in self.inports:
                msg = self.recv(inport)
                batch.append(msg)
            self.send(batch, "out_")

    def __repr__(self) -> str:
        return f"<MergeSynch name={self.name} inputs={self.num_inputs}>"

    def __str__(self) -> str:
        return f"MergeSynch({self.num_inputs} inputs)"
