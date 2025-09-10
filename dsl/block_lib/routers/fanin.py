# =================================================
#                    MergeSynch                   |
# =================================================
from typing import Optional, Any, Callable
import traceback
from rich import print as rprint

from dsl.core import Agent

DEBUG_LOG = "dsl_debug.log"


class MergeSynch(Agent):
    """
    Block with multiple inports and one outport "out".
    Waits to receive one message from EACH inport synchronously in order,
    then applies transformer_fn([msg1, msg2, ...]) and sends the result to "out".
    """

    def __init__(
        self,
        inports: list[str],
        transformer_fn: Optional[Callable[[list[Any]], Any]] = None,
        name: Optional[str] = None
    ):
        if not inports:
            raise ValueError(
                "TransformMultipleStreams requires at least one inport.")

        super().__init__(name=name or "MergeSynch",
                         inports=inports,
                         outports=["out"],
                         run=self.run)

        self.transformer_fn = transformer_fn
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
                    result = self.transformer_fn(
                        inputs) if self.transformer_fn else inputs
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
    Block with multiple inports and one outport "out".
    Processes messages as they arrive from ANY inport (asynchronously).
    Applies transformer_fn(msg, port) and sends result to "out".
    """

    def __init__(
        self,
        inports: list[str],
        transformer_fn: Optional[Callable[[Any, str], Any]] = None,
        name: Optional[str] = None
    ):
        if not inports:
            raise ValueError(
                "MergeAsynch requires at least one inport.")
        if transformer_fn is not None and not callable(transformer_fn):
            raise TypeError("transformer_fn must be a callable or None.")

        super().__init__(name=name or "MergeAsynch",
                         inports=inports,
                         outports=["out"],
                         run=self.run)

        self.transformer_fn = transformer_fn

        self.terminated_inports = {inport: False for inport in self.inports}

    def run(self):
        self.terminated_inports = {port: False for port in self.inports}

        while True:
            msg, port = self.wait_for_any_port()

            if msg == "__STOP__":
                self.terminated_inports[port] = True

                if all(self.terminated_inports[p] for p in self.inports):
                    self.send("__STOP__", "out")
                    return

                # Do not process a __STOP__ message
                continue

            try:
                result = self.transformer_fn(
                    msg, port) if self.transformer_fn else msg
                self.send(result, "out")
            except Exception as e:
                rprint(
                    f"[bold red]❌ MergeAsynch error:[/bold red] {e}")
                with open(DEBUG_LOG, "a") as f:
                    f.write("\n--- TransformMultipleStreams Error ---\n")
                    f.write(traceback.format_exc())
                self.send("__STOP__", "out")
