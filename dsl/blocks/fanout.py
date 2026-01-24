# dsl/blocks/fanout.py

from dsl.core import Agent, STOP
from typing import Optional, Any, Callable
import copy


# =================================================
#                     Broadcast                   |
# =================================================

class Broadcast(Agent):
    """
    Broadcasts any message received on inport "in_" to all defined outports.
    Useful for duplicating a stream to multiple downstream blocks.
    Makes deep copies of messages to avoid shared state issues.

    **Ports:**
    - Inports: ["in_"] (receives messages to broadcast)
    - Outports: ["out_0", "out_1", ..., "out_{N-1}"] (N numbered outputs)

    **Message Flow:**
    1. Receives message from "in_" port
    2. Creates deep copy for each output port (prevents shared state)
    3. Sends copies to all output ports
    4. On STOP, broadcasts STOP to all outputs and terminates

    **Usage:**
    Automatically inserted by graph when one node fans out to multiple nodes.
    Students typically don't create Broadcast nodes directly.
    """

    def __init__(self, num_outports: int):
        """
        Initialize Broadcast agent.

        Args:
            num_outports: Number of output ports to create
        """
        super().__init__(
            inports=["in_"],
            outports=[f"out_{i}" for i in range(num_outports)]
        )

    def __call__(self):
        """Main processing loop - broadcast each message to all outputs."""
        while True:
            msg = self.recv("in_")

            # Check for termination signal
            if msg is STOP:
                self.broadcast_stop()
                return

            # Broadcast message to all outputs (with deep copies)
            for outport in self.outports:
                outport_msg = copy.deepcopy(msg)
                self.send(outport_msg, outport=outport)

    run = __call__  # Alias for run method

# =================================================
#                  SplitBinary                    |
# =================================================


class SplitBinary(Agent):
    """
    Binary split based on predicate function.

    **NOTE:** This class is deprecated. Use the general Split class instead,
    which supports N-way routing and follows the consistent .run() pattern.

    Single inport "in_" and two outports "out_0" and "out_1"
    Splits incoming stream into two streams based on a predicate function.
    If predicate(msg) is True, msg is sent to "out_1", else to "out_0".

    **Ports:**
    - Inports: ["in_"]
    - Outports: ["out_0", "out_1"]

    **Usage:**
    This is kept for backward compatibility but new code should use Split.
    """

    def __init__(
        self,
        outports: list[str] = ["out_0", "out_1"],
        func: Optional[Callable[[Any], bool]] = None,
    ):
        """
        Initialize SplitBinary agent.

        Args:
            outports: List of two output port names
            func: Predicate function that returns bool

        Raises:
            ValueError: If func is not provided
        """
        if func is None:
            raise ValueError(
                "A predicate function must be provided for SplitBinary."
            )

        self.func = func
        super().__init__(inports=["in_"], outports=outports)

    def run(self):
        """Main processing loop - route based on predicate."""
        while True:
            msg = self.recv("in_")

            # Check for termination signal
            if msg is STOP:
                self.broadcast_stop()
                return

            # Route based on predicate
            if self.func(msg):
                outport = self.outports[1]  # True path
            else:
                outport = self.outports[0]  # False path

            self.send(msg=msg, outport=outport)


__all__ = ["Broadcast", "SplitBinary"]
