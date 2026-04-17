# dissyslab/blocks/sink.py
"""
Sink Agent: Consumes messages for side effects.

Sinks have one input and no outputs. They are terminal nodes that call
fn(msg, **params) for each message to perform side effects like printing,
saving, or collecting. Termination is signaled by os_agent via _Shutdown,
which is handled transparently by recv().
"""

from __future__ import annotations
from typing import Any, Callable, Optional, Dict
import traceback

from dissyslab.core import Agent


class Sink(Agent):
    """
    Sink agent: consumes messages for side effects.

    Single input, no outputs. Terminal node that calls fn(msg, **params)
    for each message. Used for actions like printing, saving, or sending.

    **Ports:**
    - Inports: ["in_"]
    - Outports: [] (no outputs)

    **Termination:**
    Termination is detected by os_agent and signaled via _Shutdown,
    which recv() handles transparently by raising _ShutdownSignal.
    No explicit STOP handling needed.
    """

    def __init__(
        self,
        *,
        fn: Callable[..., None],
        name: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None
    ):
        if not callable(fn):
            raise TypeError(
                f"Sink fn must be callable, got {type(fn).__name__}"
            )

        super().__init__(name=name, inports=["in_"], outports=[])
        self._fn = fn
        self._params = params or {}

    @property
    def default_inport(self) -> str:
        """Default input port for edge syntax."""
        return "in_"

    def run(self) -> None:
        """
        Process messages until _Shutdown is received.

        recv() intercepts _Shutdown and raises _ShutdownSignal,
        which unwinds this loop cleanly.
        """
        while True:
            msg = self.recv("in_")
            try:
                self._fn(msg, **self._params)
            except Exception as e:
                print(f"[Sink '{self.name}'] Error in fn: {e}")
                print(traceback.format_exc())
                return

    def __repr__(self) -> str:
        fn_name = getattr(self._fn, "__name__", repr(self._fn))
        return f"<Sink name={self.name} fn={fn_name}>"

    def __str__(self) -> str:
        return "Sink"
