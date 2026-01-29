# dsl/blocks/split.py
"""
Split Agent: Routes messages to different outputs based on function.

Split agents use a router function to determine which output port(s)
should receive each message. The router returns a list of N messages
(one per output), with None values indicating that output should not
receive the message.
"""

from __future__ import annotations
from typing import Callable, Any, Optional, List
import traceback

from dsl.core import Agent, STOP


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

    **Capabilities:**
    This pattern supports:
    - Routing: [msg, None, None] → only out_0
    - Multicast: [msg, msg, None] → both out_0 and out_1
    - Transform: [enriched_msg, None, None] → modified message to out_0
    - Filter: [None, None, None] → drop message completely

    **Message Flow:**
    - Receives message from "in_"
    - Calls fn(msg) to get list of N messages
    - Sends each non-None message to corresponding output
    - Forwards STOP to all outputs and terminates

    **Error Handling:**
    - Validates fn returns list of correct length
    - Catches exceptions in routing logic
    - Broadcasts STOP on errors

    **Examples:**

    Even/odd routing:
        >>> class EvenOddRouter:
        ...     def route(self, msg):
        ...         if msg % 2 == 0:
        ...             return [msg, None]  # Even → out_0
        ...         else:
        ...             return [None, msg]  # Odd → out_1
        >>> router = EvenOddRouter()
        >>> split = Split(fn=router.route, num_outputs=2, name="even_odd")

    Range-based routing:
        >>> class RangeRouter:
        ...     def route(self, msg):
        ...         if msg < 0:
        ...             return [msg, None, None]  # Negative
        ...         elif msg < 100:
        ...             return [None, msg, None]  # Mid-range
        ...         else:
        ...             return [None, None, msg]  # Large
        >>> router = RangeRouter()
        >>> split = Split(fn=router.route, num_outputs=3, name="range")

    Multicast (send to multiple outputs):
        >>> class MulticastRouter:
        ...     def route(self, msg):
        ...         if msg > 100:
        ...             return [msg, msg, msg]  # All outputs
        ...         elif msg > 50:
        ...             return [msg, msg, None]  # Two outputs
        ...         else:
        ...             return [msg, None, None]  # One output
        >>> router = MulticastRouter()
        >>> split = Split(fn=router.route, num_outputs=3, name="multi")
    """

    def __init__(
        self,
        *,
        fn: Callable[[Any], List[Optional[Any]]],
        num_outputs: int,
        name: str
    ):
        """
        Initialize Split agent.

        Args:
            fn: Callable that routes messages.
                Signature: fn(msg) -> List[Optional[msg]]
                Must return list of num_outputs messages
            num_outputs: Number of output ports to create
            name: Unique name for this agent (REQUIRED)

        Raises:
            ValueError: If name is empty
            TypeError: If fn is not callable
            ValueError: If num_outputs < 2
        """
        if not name:
            raise ValueError("Split agent requires a name")

        if not callable(fn):
            raise TypeError(
                f"Split fn must be callable, got {type(fn).__name__}"
            )

        if num_outputs < 2:
            raise ValueError(
                f"Split requires at least 2 outputs, got {num_outputs}"
            )

        # Create output ports: out_0, out_1, ..., out_{n-1}
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

        Calls fn(msg) to get list of messages, sends each to corresponding output.
        """
        while True:
            # Receive message
            msg = self.recv("in_")

            # Check for termination
            if msg is STOP:
                self.broadcast_stop()
                return

            try:
                # Get routing decisions
                results = self._fn(msg)

                # Validate results
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

                # Send to each output
                # (None values filtered automatically by send())
                for i, out_msg in enumerate(results):
                    self.send(out_msg, f"out_{i}")

            except Exception as e:
                print(f"[Split '{self.name}'] Error in fn: {e}")
                print(traceback.format_exc())
                self.broadcast_stop()
                return

    def __repr__(self) -> str:
        fn_name = getattr(self._fn, "__name__", repr(self._fn))
        return f"<Split name={self.name} fn={fn_name} outputs={self.num_outputs}>"

    def __str__(self) -> str:
        return f"Split({self.num_outputs} outputs)"
