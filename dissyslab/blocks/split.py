# dsl/blocks/split.py
"""
Split Agent: Routes messages to different outputs based on function.

Split agents use a router function to determine which output port(s)
should receive each message. Termination is signaled by os_agent via
_Shutdown, handled transparently by recv().
"""

from __future__ import annotations
from typing import Callable, Any, Optional, List
import traceback

from dissyslab.core import Agent


class Split(Agent):
    """
    Split agent: routes messages based on function (conditional routing).

    Single input, multiple outputs. Calls router function to determine
    which output port(s) receive each message.

    **Ports:**
    - Inports: ["in_"]
    - Outports: ["out_0", "out_1", ..., "out_{n-1}"]

    **Function Contract:**
    fn(msg) must:
    - Take a single message argument
    - Return a list of N messages (one per output)
    - None values filtered (not sent to that output)
    - Signature: fn(msg) -> List[Optional[msg]]

    **Termination:**
    Termination is detected by os_agent and signaled via _Shutdown,
    which recv() handles transparently by raising _ShutdownSignal.
    """

    def __init__(
        self,
        *,
        fn: Callable[[Any], List[Optional[Any]]],
        num_outputs: int,
        name: Optional[str] = None
    ):
        if not callable(fn):
            raise TypeError(
                f"Split fn must be callable, got {type(fn).__name__}"
            )

        if num_outputs < 2:
            raise ValueError(
                f"Split requires at least 2 outputs, got {num_outputs}"
            )

        outports = [f"out_{i}" for i in range(num_outputs)]
        super().__init__(name=name, inports=["in_"], outports=outports)
        self._fn = fn
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
        Route messages to outputs based on fn.

        recv() intercepts _Shutdown and raises _ShutdownSignal,
        which unwinds this loop cleanly.
        """
        while True:
            msg = self.recv("in_")

            try:
                results = self._fn(msg)

                if not isinstance(results, (list, tuple)):
                    raise TypeError(
                        f"Split fn must return a list of {self.num_outputs} messages. "
                        f"Got {type(results).__name__}: {results!r}"
                    )

                if len(results) != self.num_outputs:
                    raise ValueError(
                        f"Split fn must return exactly {self.num_outputs} messages. "
                        f"Got {len(results)} messages: {results!r}"
                    )

                for i, out_msg in enumerate(results):
                    self.send(out_msg, f"out_{i}")

            except Exception as e:
                print(f"[Split '{self.name}'] Error in fn: {e}")
                print(traceback.format_exc())
                return

    def __repr__(self) -> str:
        fn_name = getattr(self._fn, "__name__", repr(self._fn))
        return f"<Split name={self.name} fn={fn_name} outputs={self.num_outputs}>"

    def __str__(self) -> str:
        return f"Split({self.num_outputs} outputs)"
