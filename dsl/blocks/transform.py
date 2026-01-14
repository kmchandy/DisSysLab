# dsl/blocks/transform.py

from __future__ import annotations
import traceback
from typing import Any, Callable, Optional
from dsl.core import Agent, STOP


class Transform(Agent):
    """
    Transform Agent: Applies a function to transform messages flowing through.

    **Ports:**
    - Inports: ["in"] (receives messages to transform)
    - Outports: ["out"] (sends transformed messages)

    **Message Flow:**
    1. Receives message from "in" port
    2. Applies fn(msg) to transform it
    3. Sends result to "out" port
    4. If fn returns None, message is filtered out (not sent downstream)
    5. Forwards STOP signal downstream and terminates

    **Function Requirements:**
    The fn parameter should be a callable that:
    - Takes a single message argument: fn(msg)
    - Returns transformed message or None to filter
    - Signature: fn(msg) -> Optional[msg]

    **Filtering:**
    Returning None from fn drops the message - it won't be sent downstream.
    This enables filter patterns in the transform.

    **Error Handling:**
    - Exceptions during transformation are caught and logged
    - Transform fails fast - first error stops the pipeline
    - STOP signal is broadcast to downstream agents
    - This helps students debug issues immediately

    **State:**
    Use class methods for stateful transformations that need to maintain
    counters, caches, or other state between messages.

    **Examples:**

    Simple stateless transform:
        >>> def double(msg):
        ...     return {"value": msg["value"] * 2}
        >>> 
        >>> transform = Transform(fn=double)

    Stateful transform with class:
        >>> class Counter:
        ...     def __init__(self):
        ...         self.count = 0
        ...     
        ...     def add_index(self, msg):
        ...         self.count += 1
        ...         return {**msg, "index": self.count}
        >>> 
        >>> counter = Counter()
        >>> transform = Transform(fn=counter.add_index)

    Transform with parameters (using class):
        >>> class Scaler:
        ...     def __init__(self, factor):
        ...         self.factor = factor
        ...     
        ...     def scale(self, msg):
        ...         return {"value": msg["value"] * self.factor}
        >>> 
        >>> scaler = Scaler(10)
        >>> transform = Transform(fn=scaler.scale)

    Filter pattern (returning None drops messages):
        >>> class PositiveFilter:
        ...     def filter(self, msg):
        ...         if msg["value"] > 0:
        ...             return msg
        ...         return None  # Message filtered out
        >>> 
        >>> filter_obj = PositiveFilter()
        >>> transform = Transform(fn=filter_obj.filter)

    Text processing:
        >>> class TextCleaner:
        ...     def clean(self, msg):
        ...         import re
        ...         text = msg["text"]
        ...         cleaned = re.sub(r'[^\\w\\s.,!?-]', '', text)
        ...         return {**msg, "clean_text": cleaned}
        >>> 
        >>> cleaner = TextCleaner()
        >>> transform = Transform(fn=cleaner.clean)
    """

    def __init__(self, fn: Callable[[Any], Optional[Any]]) -> None:
        """
        Initialize a Transform agent.

        Args:
            fn: Callable that transforms messages.
                Signature: fn(msg) -> Optional[msg]
                - Takes a message as input
                - Returns transformed message, or None to filter

        Raises:
            TypeError: If fn is not callable
        """
        if not callable(fn):
            raise TypeError(
                f"Transform fn must be callable. Got {type(fn).__name__}"
            )

        super().__init__(inports=["in"], outports=["out"])
        self._fn = fn

    def __call__(self) -> None:
        """
        Main processing loop for the Transform agent.

        Receives messages, transforms them, and sends results downstream.
        """
        while True:
            msg = self.recv("in")

            # Check for termination signal
            if msg is STOP:
                self.broadcast_stop()
                return

            # Transform the message
            try:
                result = self._fn(msg)
            except Exception as e:
                print(f"[Transform] Error in fn: {e}")
                print(traceback.format_exc())
                self.broadcast_stop()
                return

            # Send result (None is automatically filtered by send())
            self.send(result, "out")

    run = __call__

    def __repr__(self) -> str:
        fn_name = getattr(self._fn, "__name__", repr(self._fn))
        return f"<Transform fn={fn_name}>"

    def __str__(self) -> str:
        return "Transform"


__all__ = ["Transform"]
