# dissyslab/blocks/fanin.py
"""
Merge Agents: Combine multiple inputs into single output (fanin).

MergeAsynch is the recommended merge for most use cases. Termination is
signaled by os_agent via _Shutdown, handled transparently by recv().
No STOP coordination needed.
"""

from __future__ import annotations
from typing import Optional
import threading

from dissyslab.core import Agent, _ShutdownSignal


class MergeAsynch(Agent):
    """
    MergeAsynch agent: combines multiple inputs (fanin, non-deterministic).

    Multiple inputs, single output. Receives from whichever input has
    a message available first. Fast but non-deterministic order.

    **Ports:**
    - Inports: ["in_0", "in_1", ..., "in_{n-1}"]
    - Outports: ["out_"]

    **Termination:**
    Termination is detected by os_agent and signaled via _Shutdown on
    each inport, handled transparently by recv(). No STOP coordination
    needed — worker threads exit cleanly via _ShutdownSignal.
    """

    def __init__(self, *, num_inputs: int, name: Optional[str] = None):
        if num_inputs < 1:
            raise ValueError(
                f"MergeAsynch requires at least 1 input, got {num_inputs}"
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

    def _worker(self, port: str) -> None:
        """
        Worker thread for one input port.
        Forwards messages to out_ until _ShutdownSignal is raised by recv().
        """
        try:
            while True:
                msg = self.recv(port)
                self.send(msg, "out_")
        except _ShutdownSignal:
            pass  # clean exit — os_agent declared termination

    def run(self) -> None:
        """
        Spawn one worker thread per input port and wait for all to finish.

        Workers exit when recv() raises _ShutdownSignal on _Shutdown receipt.
        """
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

        for t in threads:
            t.join()

    def __repr__(self) -> str:
        return f"<MergeAsynch name={self.name} inputs={self.num_inputs}>"

    def __str__(self) -> str:
        return f"MergeAsynch({self.num_inputs} inputs)"
