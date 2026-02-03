# dsl/blocks/fanin.py
"""
Merge Agents: Combine multiple inputs into single output.

MergeSynch: Synchronous merge in round-robin order (use sparingly)
MergeAsynch: Asynchronous merge as messages arrive (use for most cases)
"""

from __future__ import annotations
from typing import Optional, Set
import threading

from dsl.core import Agent, STOP


class MergeSynch(Agent):
    """
    MergeSynch agent: synchronously combines multiple inputs in round-robin order.

    **WARNING: Use only when deterministic ordering is required AND all inputs
    produce messages at similar rates. For most use cases, prefer MergeAsynch.**

    **Behavior:**
    - Collects one message from each input in round-robin order (in_0, in_1, ...)
    - Sends collected messages as a list: [msg_from_in_0, msg_from_in_1, ...]
    - Repeats until any input sends STOP
    - If STOP arrives mid-batch, discards partial batch and terminates

    **Blocking Warning:**
    This agent will BLOCK waiting for the slowest input. If inputs produce
    messages at different rates, the network will hang waiting for slow inputs.

    **Ports:**
    - Inports: ["in_0", "in_1", ..., "in_{n-1}"]
    - Outports: ["out_"]

    **Message Flow:**
    - Receives messages from inputs in deterministic round-robin order
    - Sends list of synchronized messages downstream
    - Terminates when any input sends STOP (no partial batches)

    **Examples:**

    Synchronous merge:
        >>> merge = MergeSynch(num_inputs=3, name="sync_merge")
        >>> g = network([
        ...     (source_a, merge, "in_0"),  # Must produce at same rate
        ...     (source_b, merge, "in_1"),  # as source_a and source_c
        ...     (source_c, merge, "in_2"),
        ...     (merge, sink)
        ... ])
        # Output: [[msg_a0, msg_b0, msg_c0], [msg_a1, msg_b1, msg_c1], ...]
    """

    def __init__(self, *, num_inputs: int, name: str):
        """
        Initialize MergeSynch agent.

        Args:
            num_inputs: Number of input ports to create
            name: Unique name for this agent (REQUIRED)

        Raises:
            ValueError: If name is empty
            ValueError: If num_inputs < 1
        """
        if not name:
            raise ValueError("MergeSynch agent requires a name")

        if num_inputs < 1:
            raise ValueError(
                f"MergeSynch requires at least 1 input, got {num_inputs}"
            )

        # Create input ports: in_0, in_1, ..., in_{n-1}
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

        Repeats:
        1. Collect one message from each input in order
        2. Send as a list
        3. Stop if any input sends STOP (discard partial batch)
        """
        while True:
            batch = []

            # Collect one message from each input in round-robin order
            for inport in self.inports:
                msg = self.recv(inport)

                if msg is STOP:
                    # Any input stopping means we're done
                    # Discard partial batch
                    self.broadcast_stop()
                    return

                batch.append(msg)

            # Send the synchronized batch as a list
            self.send(batch, "out_")

    def __repr__(self) -> str:
        return f"<MergeSynch name={self.name} inputs={self.num_inputs}>"

    def __str__(self) -> str:
        return f"MergeSynch({self.num_inputs} inputs)"
