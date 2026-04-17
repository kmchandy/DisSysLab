# dissyslab/blocks/fanout.py
"""
Broadcast Agent: Copies messages to multiple outputs (fanout).

Broadcast agents are automatically inserted by the framework when one
agent connects to multiple receivers. Termination is signaled by os_agent
via _Shutdown, handled transparently by recv().
"""

from __future__ import annotations
from typing import Optional
import copy

from dissyslab.core import Agent


class Broadcast(Agent):
    """
    Broadcast agent: copies messages to multiple outputs (fanout).

    Single input, multiple outputs. Receives message and sends a deep
    copy to each output port.

    **Ports:**
    - Inports: ["in_"]
    - Outports: ["out_0", "out_1", ..., "out_{n-1}"]

    **Termination:**
    Termination is detected by os_agent and signaled via _Shutdown,
    which recv() handles transparently by raising _ShutdownSignal.
    """

    def __init__(self, *, num_outputs: int, name: Optional[str] = None):
        if num_outputs < 1:
            raise ValueError(
                f"Broadcast requires at least 1 output, got {num_outputs}"
            )

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

        recv() intercepts _Shutdown and raises _ShutdownSignal,
        which unwinds this loop cleanly.
        """
        while True:
            msg = self.recv("in_")
            for i in range(self.num_outputs):
                self.send(copy.deepcopy(msg), f"out_{i}")

    def __repr__(self) -> str:
        return f"<Broadcast name={self.name} outputs={self.num_outputs}>"

    def __str__(self) -> str:
        return f"Broadcast({self.num_outputs} outputs)"
