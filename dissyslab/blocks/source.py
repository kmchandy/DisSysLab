# dissyslab/blocks/source.py
"""
Source Agent: Repeatedly calls a function to generate messages.

Sources have no inputs and generate data by calling fn() repeatedly until
it returns None. When exhausted, the source sends a termination message to
os_agent with its final sent counts. Termination is detected by os_agent —
sources do not send STOP signals.
"""

from __future__ import annotations
import inspect
import traceback
import time
from typing import Any, Callable, Optional

from dissyslab.core import Agent


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

    Generator functions are also accepted — Source wraps them automatically
    so that each call to fn() advances the generator by one step.

    **Termination:**
    When fn() returns None, the source sends a termination message to
    os_agent containing its final sent counts, then returns from run().
    os_agent uses this message to detect when all sources are done.

    **Optional Rate Limiting:**
    The interval parameter adds a delay between messages:
    - interval=0 (default): emit as fast as possible
    - interval=1.0: emit one message per second
    """

    def __init__(
        self,
        *,
        fn: Callable[[], Optional[Any]],
        name: Optional[str] = None,
        interval: float = 0
    ):
        if not callable(fn):
            raise TypeError(
                "Source fn must be callable with signature: fn() -> Optional[message]"
            )

        super().__init__(name=name, inports=[], outports=["out_"])

        # If fn is a generator function, wrap it so each call returns one item.
        if inspect.isgeneratorfunction(fn):
            _gen = fn()
            def fn(): return next(_gen, None)

        self._fn = fn
        self._interval = interval

    @property
    def default_outport(self) -> str:
        """Default output port for edge syntax."""
        return "out_"

    def _send_termination(self) -> None:
        """
        Send final sent counts to os_agent.
        Called when source is exhausted or encounters an error.
        """
        self.send_os({
            "agent":    self.name,
            "sent":     dict(self.sent),
            "received": {},
        })

    def run(self) -> None:
        """
        Main processing loop for the Source agent.

        Repeatedly calls self._fn() to get messages and emits them.
        When fn() returns None or an exception occurs, sends termination
        message to os_agent and returns.
        """
        try:
            while True:
                msg = self._fn()

                # None means the source is exhausted
                if msg is None:
                    self._send_termination()
                    return

                self.send(msg, "out_")

                if self._interval > 0:
                    time.sleep(self._interval)

        except Exception as e:
            print(f"[Source '{self.name}'] Error in fn: {e}")
            print(traceback.format_exc())
            self._send_termination()

    def __repr__(self) -> str:
        fn_name = getattr(self._fn, "__name__", repr(self._fn))
        interval_str = f", interval={self._interval}" if self._interval > 0 else ""
        return f"<Source name={self.name} fn={fn_name}{interval_str}>"

    def __str__(self) -> str:
        return "Source"
