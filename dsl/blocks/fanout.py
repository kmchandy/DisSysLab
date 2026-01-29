# dsl/blocks/fanout.py
"""
Broadcast Agent: Copies messages to multiple outputs (fanout).

Broadcast agents are automatically inserted by the framework when one
agent connects to multiple receivers.
"""

from __future__ import annotations
from typing import Optional
import copy

from dsl.core import Agent, STOP


class Broadcast(Agent):
    """
    Broadcast agent: copies messages to multiple outputs (fanout).

    Single input, multiple outputs. Receives message and sends copy
    to each output port.

    **Ports:**
    - Inports: ["in_"]
    - Outports: ["out_0", "out_1", ..., "out_{n-1}"]

    **Message Flow:**
    - Receives msg from "in_" port
    - Creates deep copy for each output
    - Sends copies to ALL output ports
    - Forwards STOP to all outputs and terminates

    **Deep Copy:**
    Each output gets an independent copy of the message to avoid
    shared state bugs when downstream agents modify messages.

    **Usage:**
    Usually auto-inserted by framework when one agent sends to multiple
    receivers. Can also be created explicitly for control.

    **Examples:**

    Explicit broadcast:
        >>> broadcast = Broadcast(num_outputs=3, name="fanout")
        >>> g = network([
        ...     (source, broadcast),
        ...     (broadcast.out_0, sink_a),
        ...     (broadcast.out_1, sink_b),
        ...     (broadcast.out_2, sink_c)
        ... ])

    Auto-inserted (framework creates broadcast automatically):
        >>> g = network([
        ...     (source, sink_a),
        ...     (source, sink_b),  # Broadcast auto-inserted here
        ...     (source, sink_c)
        ... ])
    """

    def __init__(self, *, num_outputs: int, name: str):
        """
        Initialize Broadcast agent.

        Args:
            num_outputs: Number of output ports to create
            name: Unique name for this agent (REQUIRED)

        Raises:
            ValueError: If name is empty
            ValueError: If num_outputs < 1
        """
        if not name:
            raise ValueError("Broadcast agent requires a name")

        if num_outputs < 1:
            raise ValueError(
                f"Broadcast requires at least 1 output, got {num_outputs}"
            )

        # Create output ports: out_0, out_1, ..., out_{n-1}
        outports = [f"out_{i}" for i in range(num_outputs)]

        super().__init__(name=name, inports=["in_"], outports=outports)
        self.num_outputs = num_outputs

    @property
    def default_inport(self) -> str:
        """Default input port for edge syntax."""
        return "in_"

    @property
    def default_outport(self) -> Optional[str]:
        """No default output (multiple outputs - ambiguous)."""
        return None

    def run(self) -> None:
        """
        Broadcast messages to all outputs.

        Receives from "in_", sends deep copies to all "out_*" ports.
        """
        while True:
            # Receive message
            msg = self.recv("in_")

            # Check for termination
            if msg is STOP:
                self.broadcast_stop()
                return

            # Send deep copy to each output
            # (prevents shared state bugs)
            for i in range(self.num_outputs):
                outport_msg = copy.deepcopy(msg)
                self.send(outport_msg, f"out_{i}")

    def __repr__(self) -> str:
        return f"<Broadcast name={self.name} outputs={self.num_outputs}>"

    def __str__(self) -> str:
        return f"Broadcast({self.num_outputs} outputs)"
