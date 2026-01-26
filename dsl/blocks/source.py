# dsl/blocks/source.py
"""
Source Agent: Repeatedly calls a function to generate messages.

Sources have no inputs and generate data by calling fn() repeatedly until
it returns None. This pattern supports stateful data generation via instance
methods.
"""

from __future__ import annotations
import traceback
import time
from typing import Any, Callable, Optional

from dsl.core import Agent


class Source(Agent):
    """
    Source Agent: Repeatedly calls a function to generate messages.

    **Ports:**
    - Inports: [] (no inputs - sources generate data)
    - Outports: ["out_"] (emits generated messages)

    **Function Requirements:**
    The fn callable must:
    - Return a message (any type) on each call
    - Return None when exhausted (no more messages)
    - Maintain its own state between calls (if needed)

    **Message Flow:**
    1. Calls fn() repeatedly
    2. Sends returned messages to "out_" port
    3. When fn() returns None, sends STOP and terminates

    **Optional Rate Limiting:**
    The interval parameter adds a delay between messages:
    - interval=0 (default): emit as fast as possible
    - interval=1.0: emit one message per second
    - Useful for simulating real-time streams

    **Error Handling:**
    - Exceptions during fn() are caught and logged
    - STOP signal is sent to downstream agents
    - Pipeline terminates gracefully

    **Examples:**

    Simple list source:
        >>> class ListSource:
        ...     def __init__(self, items):
        ...         self.items = items
        ...         self.index = 0
        ...     
        ...     def run(self):
        ...         if self.index >= len(self.items):
        ...             return None  # Exhausted
        ...         item = self.items[self.index]
        ...         self.index += 1
        ...         return {"value": item}
        >>> 
        >>> data = ListSource([1, 2, 3])
        >>> source = Source(fn=data.run, name="numbers")

    Counter source:
        >>> class CounterSource:
        ...     def __init__(self, max_count):
        ...         self.count = 0
        ...         self.max_count = max_count
        ...     
        ...     def run(self):
        ...         if self.count >= self.max_count:
        ...             return None
        ...         result = {"count": self.count}
        ...         self.count += 1
        ...         return result
        >>> 
        >>> counter = CounterSource(max_count=5)
        >>> source = Source(fn=counter.run, name="counter")

    With rate limiting:
        >>> data = ListSource([1, 2, 3])
        >>> source = Source(fn=data.run, interval=1.0, name="slow_src")

    Using a lambda:
        >>> items = iter([1, 2, 3])
        >>> source = Source(fn=lambda: next(items, None), name="iter_src")
    """

    def __init__(
        self, 
        *,
        fn: Callable[[], Optional[Any]], 
        name: str,
        interval: float = 0
    ):
        """
        Initialize a Source agent.

        Args:
            fn: Callable that returns messages or None when exhausted.
                Should have signature: fn() -> Optional[message]
            name: Unique name for this agent (REQUIRED)
            interval: Optional delay in seconds between messages (default: 0)

        Raises:
            ValueError: If name is empty
            TypeError: If fn is not callable
        """
        if not name:
            raise ValueError("Source agent requires a name")
        
        if not callable(fn):
            raise TypeError(
                "Source fn must be callable with signature: fn() -> Optional[message]"
            )

        super().__init__(name=name, inports=[], outports=["out_"])
        self._fn = fn
        self._interval = interval

    @property
    def default_outport(self) -> str:
        """Default output port for edge syntax."""
        return "out_"

    def run(self) -> None:
        """
        Main processing loop for the Source agent.

        Repeatedly calls self._fn() to get messages and emits them.
        Stops when fn() returns None or an exception occurs.
        """
        try:
            while True:
                # Get next message from function
                msg = self._fn()

                # None means the source is exhausted
                if msg is None:
                    self.broadcast_stop()
                    return

                # Send the message downstream
                self.send(msg, "out_")

                # Optional rate limiting
                if self._interval > 0:
                    time.sleep(self._interval)

        except Exception as e:
            # Log error and terminate gracefully
            print(f"[Source '{self.name}'] Error in fn: {e}")
            print(traceback.format_exc())
            self.broadcast_stop()

    def __repr__(self) -> str:
        fn_name = getattr(self._fn, "__name__", repr(self._fn))
        interval_str = f", interval={self._interval}" if self._interval > 0 else ""
        return f"<Source name={self.name} fn={fn_name}{interval_str}>"

    def __str__(self) -> str:
        return "Source"