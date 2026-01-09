# dsl/blocks/source.py

from __future__ import annotations
import traceback
import time
from typing import Any, Callable, Optional
from dsl.core import Agent, STOP


class Source(Agent):
    """
    Source Agent: Repeatedly calls a function to generate messages.

    **Ports:**
    - Inports: [] (no inputs - sources generate data)
    - Outports: ["out"] (emits generated messages)

    **Function Requirements:**
    The fn callable must:
    - Return a message (typically a dict) on each call
    - Return None when exhausted (no more messages)
    - Maintain its own state between calls (if needed)

    **Message Flow:**
    1. Calls fn() repeatedly
    2. Sends returned messages to "out" port
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

    **Consistent Pattern:**
    All agents now use the same pattern:
        source = Source(fn=data_source.run)
        transform = Transform(fn=processor.run)
        sink = Sink(fn=handler.run)

    This makes the API uniform and easier to teach.

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
        >>> source = Source(fn=data.run)  # ← Consistent with Transform/Sink!

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
        >>> source = Source(fn=counter.run)

    With rate limiting:
        >>> data = ListSource([1, 2, 3])
        >>> source = Source(fn=data.run, interval=1.0)  # One per second

    Using a lambda:
        >>> # Simple inline source
        >>> items = iter([1, 2, 3])
        >>> source = Source(fn=lambda: next(items, None))
    """

    def __init__(self, *, fn: Callable[[], Optional[Any]], interval: float = 0):
        """
        Initialize a Source agent.

        Args:
            fn: Callable that returns messages or None when exhausted.
                Should have signature: fn() -> Optional[message]
            interval: Optional delay in seconds between messages (default: 0)

        Raises:
            TypeError: If fn is not callable

        Examples:
            >>> data = ListSource([1, 2, 3])
            >>> source = Source(fn=data.run)
            >>> 
            >>> # With rate limiting
            >>> source = Source(fn=data.run, interval=1.0)
        """
        if not callable(fn):
            raise TypeError(
                "Source(fn=...) must be callable with signature fn() -> Optional[message]"
            )

        super().__init__(inports=[], outports=["out"])
        self._fn = fn
        self._interval = interval

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
                    self.send(STOP, "out")
                    return

                # Send the message downstream
                self.send(msg, "out")

                # Optional rate limiting
                if self._interval > 0:
                    time.sleep(self._interval)

        except Exception as e:
            # Log error and terminate gracefully
            print(f"[Source] Error during fn(): {e}")
            print(traceback.format_exc())
            self.send(STOP, "out")

    def __repr__(self) -> str:
        fn_name = getattr(self._fn, "__name__", repr(self._fn))
        interval_str = f", interval={self._interval}" if self._interval > 0 else ""
        return f"<Source fn={fn_name}{interval_str}>"

    def __str__(self) -> str:
        return "Source"


__all__ = ["Source"]
