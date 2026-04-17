# dsl/blocks/transform.py
"""
Transform Agent: Applies a function to transform messages.

Transforms have one input and one output. They process each message by
calling fn(msg, **params) and sending the result downstream. Termination
is signaled by os_agent via _Shutdown, handled transparently by recv().
"""

from __future__ import annotations
from typing import Any, Callable, Optional, Dict
import traceback

from dissyslab.core import Agent


class Transform(Agent):
    """
    Transform agent: applies a function to each message.

    Single input, single output. Processes each message by calling
    fn(msg, **params) and sending the result.

    **Ports:**
    - Inports: ["in_"]
    - Outports: ["out_"]

    **Termination:**
    Termination is detected by os_agent and signaled via _Shutdown,
    which recv() handles transparently by raising _ShutdownSignal.
    No explicit STOP handling needed.
    """

    def __init__(
        self,
        *,
        fn: Callable[..., Optional[Any]],
        name: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None
    ):
        if not callable(fn):
            raise TypeError(
                f"Transform fn must be callable, got {type(fn).__name__}"
            )

        super().__init__(name=name, inports=["in_"], outports=["out_"])
        self._fn = fn
        self._params = params or {}

    @property
    def default_inport(self) -> str:
        """Default input port for edge syntax."""
        return "in_"

    @property
    def default_outport(self) -> str:
        """Default output port for edge syntax."""
        return "out_"

    def run(self) -> None:
        """
        Process messages until _Shutdown is received.

        recv() intercepts _Shutdown and raises _ShutdownSignal,
        which unwinds this loop cleanly.
        """
        while True:
            msg = self.recv("in_")
            try:
                result = self._fn(msg, **self._params)
            except Exception as e:
                print(f"[Transform '{self.name}'] Error in fn: {e}")
                print(traceback.format_exc())
                return
            self.send(result, "out_")

    def __repr__(self) -> str:
        fn_name = getattr(self._fn, "__name__", repr(self._fn))
        return f"<Transform name={self.name} fn={fn_name}>"

    def __str__(self) -> str:
        return "Transform"
