# dsl/blocks/split.py

from __future__ import annotations
import traceback
from typing import Any, Callable, List, Optional
from dsl.core import Agent, STOP


class Split(Agent):
    """
    Split Agent: Route messages to N outputs based on router function.

    **Ports:**
    - Inports: ["in_"] (receives messages to route)
    - Outports: ["out_0", "out_1", ..., "out_{N-1}"] (N numbered outputs)

    **Function Requirements:**
    The fn parameter should be a callable that:
    - Takes a single message argument: fn(msg)
    - Returns a list of N messages (one per output port)
    - None values in the list are filtered (not sent to that output)
    - Signature: fn(msg) -> List[Optional[msg]]

    **Capabilities:**
    This pattern allows:
    - Routing to one output: [msg, None, None]
    - Routing to multiple outputs: [msg, msg, None] (multicast)
    - Transforming while routing: [enriched_msg, None, None]
    - Complex routing logic with state

    **Message Flow:**
    1. Receives message from "in_" port
    2. Calls fn(msg) to get list of N messages
    3. Sends each non-None message to corresponding output port
    4. If fn returns None for a position, that output is filtered
    5. Forwards STOP signal to all outputs and terminates

    **Error Handling:**
    - Validates that fn returns a list of correct length
    - Catches exceptions in routing logic
    - Broadcasts STOP on errors

    **Examples:**

    Simple content routing:
        >>> class ContentRouter:
        ...     def route(self, msg):
        ...         if is_spam(msg["text"]):
        ...             return [msg, None, None]  # Route to spam handler
        ...         elif is_abuse(msg["text"]):
        ...             return [None, msg, None]  # Route to abuse handler
        ...         else:
        ...             return [None, None, msg]  # Route to safe handler
        >>> 
        >>> router = ContentRouter()
        >>> split = Split(fn=router.route, num_outputs=3)

    Sentiment-based routing:
        >>> class SentimentRouter:
        ...     def route(self, msg):
        ...         score = analyze_sentiment(msg["text"])
        ...         if score > 0.5:
        ...             return [msg, None, None]  # Positive
        ...         elif score < -0.5:
        ...             return [None, msg, None]  # Negative
        ...         else:
        ...             return [None, None, msg]  # Neutral
        >>> 
        >>> router = SentimentRouter()
        >>> split = Split(fn=router.route, num_outputs=3)

    Round-robin routing:
        >>> class RoundRobinRouter:
        ...     def __init__(self, num_outputs):
        ...         self.num_outputs = num_outputs
        ...         self.counter = 0
        ...     
        ...     def route(self, msg):
        ...         results = [None] * self.num_outputs
        ...         results[self.counter % self.num_outputs] = msg
        ...         self.counter += 1
        ...         return results
        >>> 
        >>> router = RoundRobinRouter(num_outputs=3)
        >>> split = Split(fn=router.route, num_outputs=3)

    Multicast to multiple handlers:
        >>> class AlertRouter:
        ...     def route(self, msg):
        ...         if msg["priority"] == "critical":
        ...             return [msg, msg, msg]  # Send to all handlers
        ...         elif msg["priority"] == "high":
        ...             return [msg, msg, None]  # Send to two handlers
        ...         else:
        ...             return [msg, None, None]  # Send to one handler
        >>> 
        >>> router = AlertRouter()
        >>> split = Split(fn=router.route, num_outputs=3)

    Transform while routing:
        >>> class EnrichingRouter:
        ...     def __init__(self):
        ...         self.count = 0
        ...     
        ...     def route(self, msg):
        ...         self.count += 1
        ...         category = self.categorize(msg["text"])
        ...         enriched = {
        ...             **msg, 
        ...             "category": category,
        ...             "index": self.count
        ...         }
        ...         
        ...         if category == "spam":
        ...             return [enriched, None]
        ...         else:
        ...             return [None, enriched]
        >>> 
        >>> router = EnrichingRouter()
        >>> split = Split(fn=router.route, num_outputs=2)
    """

    def __init__(self, fn: Callable[[Any], List[Optional[Any]]], *, num_outputs: int) -> None:
        """
        Initialize a Split agent.

        Args:
            fn: Callable that routes messages to outputs.
                Signature: fn(msg) -> List[Optional[msg]]
                - Takes a message as input
                - Returns list of N messages (one per output)
                - None values are filtered (not sent to that output)
            num_outputs: Number of output ports to create.

        Raises:
            TypeError: If fn is not callable
            ValueError: If num_outputs < 2
        """
        if not callable(fn):
            raise TypeError(
                f"Split fn must be callable. Got {type(fn).__name__}"
            )

        if num_outputs < 2:
            raise ValueError(
                f"Split requires at least 2 outputs, got {num_outputs}"
            )

        super().__init__(
            inports=["in_"],
            outports=[f"out_{i}" for i in range(num_outputs)]
        )
        self._fn = fn
        self.num_outputs = num_outputs

    def __call__(self) -> None:
        """
        Main processing loop for the Split agent.

        Receives messages, routes them via fn, and sends to outputs.
        """
        while True:
            msg = self.recv("in_")

            # Check for termination signal
            if msg is STOP:
                self.broadcast_stop()
                return

            try:
                # Get routing decisions from function
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

                # Send to each output port
                # (None values are automatically filtered by send())
                for i, out_msg in enumerate(results):
                    self.send(out_msg, f"out_{i}")

            except Exception as e:
                print(f"[Split] Error in fn: {e}")
                print(traceback.format_exc())
                self.broadcast_stop()
                return

    run = __call__

    def __repr__(self) -> str:
        fn_name = getattr(self._fn, "__name__", repr(self._fn))
        return f"<Split fn={fn_name} num_outputs={self.num_outputs}>"

    def __str__(self) -> str:
        return f"Split({self.num_outputs} outputs)"


__all__ = ["Split"]
