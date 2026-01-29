# dsl/blocks/fanin.py
"""
Merge Agents: Combine multiple inputs into single output (fanin).

MergeAsynch is the recommended merge for most use cases - it's fast and
automatically inserted by the framework when multiple senders connect to
one receiver.
"""

from __future__ import annotations
from typing import Optional, Set
import threading

from dsl.core import Agent, STOP


class MergeAsynch(Agent):
    """
    MergeAsynch agent: combines multiple inputs (fanin, non-deterministic).

    Multiple inputs, single output. Receives from whichever input has
    a message available first. Fast but non-deterministic order.

    **This is the recommended merge for most use cases.**
    Automatically inserted when multiple nodes feed into one node.

    **Ports:**
    - Inports: ["in_0", "in_1", ..., "in_{n-1}"]
    - Outports: ["out_"]

    **Message Flow:**
    - Receives from any "in_*" port (whichever is ready first)
    - Immediately forwards each message to "out_" port
    - Waits for STOP from ALL inputs before sending final STOP
    - Uses threading to handle multiple inputs concurrently

    **Key Feature:**
    Emits single STOP downstream only after receiving STOP from all inputs.
    This ensures proper shutdown coordination in complex graphs.

    **Ordering:**
    Non-deterministic - depends on which input produces messages fastest.

    **Threading:**
    - One worker thread per input port
    - Thread-safe message forwarding
    - Clean shutdown coordination

    **Examples:**

    Explicit merge:
        >>> merge = MergeAsynch(num_inputs=3, name="combine")
        >>> g = network([
        ...     (source_a, merge.in_0),
        ...     (source_b, merge.in_1),
        ...     (source_c, merge.in_2),
        ...     (merge, sink)
        ... ])

    Auto-inserted (framework creates merge automatically):
        >>> g = network([
        ...     (source_a, sink),
        ...     (source_b, sink),  # Merge auto-inserted here
        ...     (source_c, sink)
        ... ])
    """

    def __init__(self, *, num_inputs: int, name: str):
        """
        Initialize MergeAsynch agent.

        Args:
            num_inputs: Number of input ports to create
            name: Unique name for this agent (REQUIRED)

        Raises:
            ValueError: If name is empty
            ValueError: If num_inputs < 1
        """
        if not name:
            raise ValueError("MergeAsynch agent requires a name")

        if num_inputs < 1:
            raise ValueError(
                f"MergeAsynch requires at least 1 input, got {num_inputs}"
            )

        # Create input ports: in_0, in_1, ..., in_{n-1}
        inports = [f"in_{i}" for i in range(num_inputs)]

        super().__init__(name=name, inports=inports, outports=["out_"])
        self.num_inputs = num_inputs

        # Threading for shutdown coordination
        self._stop_lock = threading.Lock()
        self._stopped_ports: Set[str] = set()
        self._all_stopped = threading.Event()

    @property
    def default_inport(self) -> Optional[str]:
        """No default input (multiple inputs - ambiguous)."""
        return None

    @property
    def default_outport(self) -> str:
        """Default output port for edge syntax."""
        return "out_"

    def _worker(self, port: str) -> None:
        """
        Worker thread for one input port.

        Continuously receives messages from port and forwards them.
        Stops when STOP received, coordinates with other workers.
        """
        while True:
            msg = self.recv(port)  # Blocking read

            # Check for termination
            if msg is STOP:
                with self._stop_lock:
                    self._stopped_ports.add(port)
                    if len(self._stopped_ports) == len(self.inports):
                        self._all_stopped.set()
                break

            # Forward message immediately (asynchronous)
            self.send(msg, "out_")

    def run(self) -> None:
        """
        Main loop.

        Spawns worker threads for each input, waits for all to finish,
        then sends final STOP downstream.
        """
        # Spawn worker thread for each input
        threads = []
        for p in self.inports:
            t = threading.Thread(
                target=self._worker,
                args=(p,),
                name=f"merge_worker_{p}",
                daemon=False
            )
            t.start()
            threads.append(t)

        # Wait until all inputs delivered STOP
        self._all_stopped.wait()

        # Clean shutdown of workers
        for t in threads:
            t.join()

        # Emit single STOP downstream
        self.send(STOP, "out_")

    def __repr__(self) -> str:
        return f"<MergeAsynch name={self.name} inputs={self.num_inputs}>"

    def __str__(self) -> str:
        return f"MergeAsynch({self.num_inputs} inputs)"
