# dsl/blocks/fanin.py

from __future__ import annotations
from typing import Set
import threading

from dsl.core import Agent, STOP


# =================================================
#                   MergeAsynch                   |
# =================================================

class MergeAsynch(Agent):
    """
    Asynchronous N→1 merge of message streams.

    **This is the recommended merge for most use cases.**
    Automatically inserted by graph when multiple nodes feed into one node.

    **Ports:**
    - Inports: ["in_0", "in_1", ..., "in_{N-1}"] (N numbered inputs)
    - Outports: ["out"]

    **Message Flow:**
    1. Receives messages from any inport as they arrive (asynchronous)
    2. Immediately forwards each message to output
    3. Waits for STOP from ALL inports before sending final STOP
    4. Uses threading to handle multiple inputs concurrently

    **Key Feature:**
    Emits a single STOP downstream only after receiving STOP from all inports.
    This ensures proper shutdown coordination in complex graphs.

    **Usage:**
    Automatically inserted by graph. Students typically don't create this directly.
    """

    def __init__(self, num_inports: int):
        """
        Initialize MergeAsynch agent.

        Args:
            num_inports: Number of input ports to create

        Raises:
            ValueError: If num_inports < 2
        """
        if num_inports < 2:
            raise ValueError("MergeAsynch requires at least two inports.")

        inports = [f"in_{i}" for i in range(num_inports)]
        super().__init__(inports=inports, outports=["out"])

        # Threading / shutdown coordination
        self._stop_lock = threading.Lock()
        self._stopped_ports: Set[str] = set()
        self._all_stopped = threading.Event()

    def _worker(self, port: str) -> None:
        """Worker thread for one input port."""
        while True:
            msg = self.recv(port)  # Blocking read from inport queue

            # Check for termination signal
            if msg is STOP:
                with self._stop_lock:
                    self._stopped_ports.add(port)
                    if len(self._stopped_ports) == len(self.inports):
                        self._all_stopped.set()
                break

            # Forward message immediately (asynchronous)
            self.send(msg, "out")

    def __call__(self) -> None:
        """Main loop - spawn worker threads for each input port."""
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

        # Wait until all inports have delivered STOP
        self._all_stopped.wait()

        # Clean shutdown of workers
        for t in threads:
            t.join()

        # Emit a single STOP downstream
        self.send(STOP, "out")

    run = __call__


__all__ = ["MergeAsynch"]
