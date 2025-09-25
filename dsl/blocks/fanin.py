# dsl/blocks/fanin.py
# =================================================
#                    MergeSynch                   |
# =================================================
from __future__ import annotations
from typing import Any, Callable, Optional, Set
import traceback
from rich import print as rprint
import threading

from dsl.core import Agent, STOP


class MergeSynch(Agent):
    """
    Block with multiple inports and one outport "out".
    Waits to receive one message from EACH inport synchronously in order,
    then applies func([msg1, msg2, ...]) and sends the result to "out".
    """

    def __init__(
        self,
        inports: list[str],
        func: Optional[Callable[[list[Any]], Any]] = None,
        name: Optional[str] = None
    ):
        if not inports:
            raise ValueError(
                "TransformMultipleStreams requires at least one inport.")

        super().__init__(name=name or "MergeSynch",
                         inports=inports,
                         outports=["out"],
                         run=self.run)

        self.func = func
        self.buffers = {port: [] for port in inports}

    def run(self):
        while True:
            for port in self.inports:
                msg = self.recv(port)
                if msg == "__STOP__":
                    self.send("__STOP__", "out")
                    return
                self.buffers[port].append(msg)

            if all(self.buffers[port] for port in self.inports):
                inputs = [self.buffers[port].pop(0) for port in self.inports]
                try:
                    result = self.func(
                        inputs) if self.func else inputs
                    self.send(result, "out")
                except Exception as e:
                    rprint(
                        f"[bold red]❌ TransformMergeSynch error:[/bold red] {e}")
                    with open(DEBUG_LOG, "a") as f:
                        f.write("\n--- TransformMergeSynch Error ---\n")
                        f.write(traceback.format_exc())
                    self.send("__STOP__", "out")


# =================================================
#                   MergeAsynch                   |
# =================================================

class MergeAsynch(Agent):
    """
    Asynchronous N→1 merge of message streams.
    Emits a single STOP after receiving STOP from all inports.
    """

    def __init__(self, num_inports: int):
        if num_inports < 2:
            raise ValueError("MergeAsynch requires at least two inports.")
        inports = [f"in_{i}" for i in range(num_inports)]
        super().__init__(inports=inports, outports=["out"])

        # Threading / shutdown coordination
        self._stop_lock = threading.Lock()
        self._stopped_ports: Set[str] = set()
        self._all_stopped = threading.Event()

    def _worker(self, port: str) -> None:
        while True:
            msg = self.recv(port)  # blocking read from inport queue
            if msg == STOP:
                with self._stop_lock:
                    self._stopped_ports.add(port)
                    if len(self._stopped_ports) == len(self.inports):
                        self._all_stopped.set()
                break
            # forward message
            self.send(msg, "out")

    def run(self) -> None:
        threads = []
        for p in self.inports:
            t = threading.Thread(
                target=self._worker,
                args=(p,),
                name=f"merge_worker_{p}",
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
