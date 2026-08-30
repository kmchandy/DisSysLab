# dissyslab/blocks/role.py
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
from typing import Callable, Any, Optional, List, Tuple, Dict
import sys
import traceback

from dissyslab.core import Agent


def normalise_results(results: Any) -> Optional[List[Tuple[Any, str]]]:
    """The four shapes a role function may return, as one list of pairs.

    ``None`` means "drop this message" and is returned unchanged, so a
    caller can tell it apart from an empty list.

    This lives at module level rather than inside ``Role.run`` because
    it now has two callers: the agent loop, and ``library.guard``, which
    composes checks around another role's function and has to read its
    return value the same way. Two copies of this rule would drift, and
    the drift would appear as a guarded role behaving differently from
    the same role unguarded -- the one thing a guard must never do.
    """
    if results is None:
        return None
    if not isinstance(results, (list, tuple)):
        return [(results, "all")]
    if results and not isinstance(results[0], (list, tuple)):
        return [(item, "all") for item in results]
    return [(pair[0], pair[1]) for pair in results]


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
        status_aliases: Optional[Dict[str, str]] = None,
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

        # Single-output convention: one status -> "out_"; multi -> indexed.
        # This matches Source's single outport name and keeps the runtime
        # port names consistent across the framework.
        if len(statuses) == 1:
            outports = ["out_"]
            self._status_to_port: dict = {statuses[0]: "out_"}
        else:
            outports = [f"out_{i}" for i in range(len(statuses))]
            self._status_to_port = {
                status: f"out_{i}"
                for i, status in enumerate(statuses)
            }

        # Optional extra names for an existing status -- e.g. a generator
        # normalized a transform's single outbox to "out" at build time, but
        # the approved fn's code was written against the original name it
        # was given (e.g. "alert"). Both then route to the same port; this
        # never creates a new port, only a second spelling for one that
        # already exists.
        self.status_aliases = dict(status_aliases or {})
        for alias, canonical in self.status_aliases.items():
            if alias in self._status_to_port:
                raise ValueError(
                    f"Role status_aliases: {alias!r} is already a declared "
                    f"status ({statuses}); an alias can't shadow a real one."
                )
            if canonical not in self._status_to_port:
                raise ValueError(
                    f"Role status_aliases: alias {alias!r} points at "
                    f"{canonical!r}, which isn't a declared status "
                    f"({statuses})."
                )
            self._status_to_port[alias] = self._status_to_port[canonical]

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
                results = normalise_results(self._fn(msg))

                if results is None:
                    continue

                for out_msg, status in results:
                    if status not in self._status_to_port:
                        accepted = list(self.statuses) + list(self.status_aliases)
                        raise ValueError(
                            f"Role '{self.name}' returned undeclared status "
                            f"'{status}'. Accepted statuses: {accepted}"
                        )
                    self.send(out_msg, self._status_to_port[status])

            except Exception as e:
                # One bad message costs that message, not the agent.
                # The behaviour and the reasoning live in
                # Agent.report_failure -- five blocks had their own
                # copy of this, and so had their own copy of the hang.
                self.report_failure(e, doing="its role")
                continue

    def __repr__(self) -> str:
        fn_name = getattr(self._fn, "__name__", repr(self._fn))
        return (
            f"<Role name={self.name} fn={fn_name} "
            f"statuses={self.statuses}>"
        )

    def __str__(self) -> str:
        return f"Role({self.statuses})"
