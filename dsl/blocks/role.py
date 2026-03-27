# dsl/blocks/role.py
"""
Role Agent: Routes messages based on status strings.

A Role agent is a generalization of Split where:
- The function returns an arbitrary list of (message, status) pairs
- Status strings determine which outport each message goes to
- The number of output messages is independent of the number of outports

Termination is signaled by os_agent via _Shutdown, handled transparently
by recv(). No explicit STOP handling needed.
"""

from __future__ import annotations
from typing import Callable, Any, Optional, List, Tuple
import traceback

from dsl.core import Agent


class Role(Agent):
    """
    Role agent: routes messages based on status strings.

    Single input, multiple outputs. The function returns either:
    (1) an arbitrary list of (message, status) pairs, or
    (2) a list of messages without explicit status values — coerced to "all", or
    (3) a single message (not a list) — treated as [(message, "all")], or
    (4) None — message is dropped.

    **Ports:**
    - Inports: ["in_"]
    - Outports: ["out_0", "out_1", ..., "out_{n-1}"]
      where n = len(statuses)

    **Termination:**
    Termination is detected by os_agent and signaled via _Shutdown,
    which recv() handles transparently by raising _ShutdownSignal.
    """

    def __init__(
        self,
        *,
        fn: Callable[[Any], List[Tuple[Any, str]]],
        statuses: List[str],
        name: Optional[str] = None
    ):
        if not callable(fn):
            raise TypeError(
                f"Role fn must be callable, got {type(fn).__name__}"
            )

        if not statuses:
            statuses = ["all"]

        if len(set(statuses)) != len(statuses):
            raise ValueError(
                f"Role statuses must be unique, got duplicates: {statuses}"
            )

        self._status_to_port: dict = {
            status: f"out_{i}" for i, status in enumerate(statuses)
        }

        outports = [f"out_{i}" for i in range(len(statuses))]

        super().__init__(name=name, inports=["in_"], outports=outports)
        self._fn = fn
        self.statuses = list(statuses)

    def run(self) -> None:
        """
        Process messages and route by status.

        recv() intercepts _Shutdown and raises _ShutdownSignal,
        which unwinds this loop cleanly.
        """
        while True:
            msg = self.recv("in_")

            try:
                results = self._fn(msg)

                if results is None:
                    continue

                if not isinstance(results, (list, tuple)):
                    results = [(results, "all")]
                elif results and not isinstance(results[0], (list, tuple)):
                    results = [(item, "all") for item in results]

                for out_msg, status in results:
                    if status not in self._status_to_port:
                        raise ValueError(
                            f"Role '{self.name}' returned undeclared status "
                            f"'{status}'. Declared statuses: {self.statuses}"
                        )
                    self.send(out_msg, self._status_to_port[status])

            except Exception as e:
                print(f"[Role '{self.name}'] Error in fn: {e}")
                print(traceback.format_exc())
                return

    def __repr__(self) -> str:
        fn_name = getattr(self._fn, "__name__", repr(self._fn))
        return (
            f"<Role name={self.name} fn={fn_name} "
            f"statuses={self.statuses}>"
        )

    def __str__(self) -> str:
        return f"Role({self.statuses})"
