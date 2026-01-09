# dsl/blocks/sink.py

from __future__ import annotations
import traceback
from typing import Any, Callable
from dsl.core import Agent, STOP


class Sink(Agent):
    """
    Sink Agent: Terminal node that consumes messages without producing output.

    **Ports:**
    - Inports: ["in"] (receives messages to consume)
    - Outports: [] (no outputs - this is a terminal node)

    **Message Flow:**
    1. Receives messages from "in" port
    2. Calls fn(msg) for each message
    3. Filters out None messages (not passed to fn)
    4. Stops when STOP signal received
    5. Closes input queue on termination

    **Function Requirements:**
    The fn parameter should be a callable that:
    - Takes a single message argument: fn(msg)
    - Returns nothing (return value is ignored)
    - Typically prints, saves to file, or collects results

    **Error Handling:**
    - Exceptions during fn(msg) are caught and logged
    - Pipeline terminates gracefully on errors
    - STOP signal always triggers clean termination
    - Input queue is closed properly on STOP

    **Examples:**

    Simple print sink:
        >>> def print_msg(msg):
        ...     print(f"Received: {msg}")
        >>> 
        >>> sink = Sink(fn=print_msg)

    Collector sink:
        >>> results = []
        >>> def collect(msg):
        ...     results.append(msg)
        >>> 
        >>> sink = Sink(fn=collect)

    File writer sink:
        >>> def write_to_file(msg):
        ...     with open("output.txt", "a") as f:
        ...         f.write(str(msg) + "\\n")
        >>> 
        >>> sink = Sink(fn=write_to_file)

    Stateful sink (using class method):
        >>> class ResultCollector:
        ...     def __init__(self):
        ...         self.results = []
        ...         self.count = 0
        ...     
        ...     def process(self, msg):
        ...         self.count += 1
        ...         self.results.append(msg)
        ...         if self.count % 10 == 0:
        ...             print(f"Processed {self.count} messages")
        >>> 
        >>> collector = ResultCollector()
        >>> sink = Sink(fn=collector.process)
    """

    def __init__(self, *, fn: Callable[[Any], None]) -> None:
        """
        Initialize a Sink agent.

        Args:
            fn: Callable that processes each message. 
                Signature: fn(msg) -> None
                Return value is ignored.

        Raises:
            TypeError: If fn is not callable
        """
        if not callable(fn):
            raise TypeError(
                f"Sink fn must be callable. Got {type(fn).__name__}"
            )

        super().__init__(inports=["in"], outports=[])
        self._fn = fn

    def run(self) -> None:
        """
        Main processing loop for the Sink agent.

        Receives messages and passes them to fn until STOP is received.
        """
        try:
            while True:
                msg = self.recv("in")

                # Check for termination signal
                if msg is STOP:
                    try:
                        self.close("in")
                    finally:
                        return

                # Filter out None messages (don't pass to fn)
                if msg is None:
                    continue

                # Process the message
                try:
                    self._fn(msg)
                except Exception as e:
                    print(f"[Sink] Error in fn: {e}")
                    print(traceback.format_exc())
                    return

        except Exception as e:
            print(f"[Sink] Error: {e}")
            print(traceback.format_exc())
            return

    def __repr__(self) -> str:
        fn_name = getattr(self._fn, "__name__", repr(self._fn))
        return f"<Sink fn={fn_name}>"

    def __str__(self) -> str:
        return "Sink"


__all__ = ["Sink"]
