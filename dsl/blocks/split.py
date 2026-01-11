# dsl/blocks/split.py

from __future__ import annotations
import traceback
from typing import Any, List, Optional, Union
from dsl.core import Agent, STOP


class Split(Agent):
    """
    Split Agent: Route messages to N outputs based on router decisions.

    **Ports:**
    - Inports: ["in"] (receives messages to route)
    - Outports: ["out_0", "out_1", ..., "out_{N-1}"] (N numbered outputs)

    **Router Requirements:**
    The router object must have a .run(msg) method that returns a list of N messages,
    where each message is sent to the corresponding output port.

    If a message in the list is None, it's filtered (not sent to that output).

    **Capabilities:**
    This pattern allows:
    - Routing to one output: [msg, None, None]
    - Routing to multiple outputs: [msg, msg, None] (multicast)
    - Transforming while routing: [enriched_msg, None, None]
    - Complex routing logic with state

    **Message Flow:**
    1. Receives message from "in" port
    2. Calls router.run(msg) to get list of N messages
    3. Sends each non-None message to corresponding output port
    4. If router returns None for a position, that output is filtered
    5. Forwards STOP signal to all outputs and terminates

    **Error Handling:**
    - Validates that router returns a list of correct length
    - Catches exceptions in router logic
    - Broadcasts STOP on errors

    **Examples:**

    Simple content routing:
        >>> class ContentRouter:
        ...     def run(self, msg):
        ...         if is_spam(msg["text"]):
        ...             return [msg, None, None]  # Route to spam handler
        ...         elif is_abuse(msg["text"]):
        ...             return [None, msg, None]  # Route to abuse handler
        ...         else:
        ...             return [None, None, msg]  # Route to safe handler
        >>> 
        >>> router = ContentRouter()
        >>> split = Split(router=router, num_outputs=3)

    Sentiment-based routing:
        >>> class SentimentRouter:
        ...     def run(self, msg):
        ...         score = analyze_sentiment(msg["text"])
        ...         if score > 0.5:
        ...             return [msg, None, None]  # Positive
        ...         elif score < -0.5:
        ...             return [None, msg, None]  # Negative
        ...         else:
        ...             return [None, None, msg]  # Neutral
        >>> 
        >>> router = SentimentRouter()
        >>> split = Split(router=router, num_outputs=3)

    Multicast to multiple handlers:
        >>> class AlertRouter:
        ...     def run(self, msg):
        ...         if msg["priority"] == "critical":
        ...             return [msg, msg, msg]  # Send to all handlers
        ...         elif msg["priority"] == "high":
        ...             return [msg, msg, None]  # Send to two handlers
        ...         else:
        ...             return [msg, None, None]  # Send to one handler
        >>> 
        >>> router = AlertRouter()
        >>> split = Split(router=router, num_outputs=3)

    Transform while routing:
        >>> class EnrichingRouter:
        ...     def __init__(self):
        ...         self.count = 0
        ...     
        ...     def run(self, msg):
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
        >>> split = Split(router=router, num_outputs=2)
    """

    def __init__(self, *, router: Any, num_outputs: int) -> None:
        """
        Initialize a Split agent.

        Args:
            router: Object with .run(msg) method that returns list of N messages.
                    Each message in the list corresponds to an output port.
                    None values are filtered (not sent).
            num_outputs: Number of output ports to create.

        Raises:
            AttributeError: If router doesn't have .run() method
            ValueError: If num_outputs < 2
        """
        if num_outputs < 2:
            raise ValueError(
                f"Split requires at least 2 outputs, got {num_outputs}"
            )

        if not hasattr(router, 'run'):
            raise AttributeError(
                f"Router must have .run(msg) method. "
                f"Got {type(router).__name__} with no .run() method."
            )

        if not callable(router.run):
            raise AttributeError(
                f"Router.run must be callable. "
                f"Got {type(router.run).__name__}"
            )

        super().__init__(
            inports=["in"],
            outports=[f"out_{i}" for i in range(num_outputs)]
        )
        self.router = router
        self.num_outputs = num_outputs

    def run(self) -> None:
        """
        Main processing loop for the Split agent.

        Receives messages, routes them via router, and sends to outputs.
        """
        while True:
            msg = self.recv("in")

            # Check for termination signal
            if msg is STOP:
                self.broadcast_stop()
                return

            try:
                # Get routing decisions from router
                results = self.router.run(msg)

                # Validate results
                if not isinstance(results, (list, tuple)):
                    raise TypeError(
                        f"Router.run() must return a list of {self.num_outputs} messages. "
                        f"Got {type(results).__name__}: {results!r}"
                    )

                if len(results) != self.num_outputs:
                    raise ValueError(
                        f"Router.run() must return exactly {self.num_outputs} messages. "
                        f"Got {len(results)} messages: {results!r}"
                    )

                # Send to each output port
                # (None values are automatically filtered by send())
                for i, out_msg in enumerate(results):
                    self.send(out_msg, f"out_{i}")

            except Exception as e:
                print(f"[Split] Error in router: {e}")
                print(traceback.format_exc())
                self.broadcast_stop()
                return

    def __repr__(self) -> str:
        router_name = type(self.router).__name__
        return f"<Split router={router_name} num_outputs={self.num_outputs}>"

    def __str__(self) -> str:
        return f"Split({self.num_outputs} outputs)"


__all__ = ["Split"]
