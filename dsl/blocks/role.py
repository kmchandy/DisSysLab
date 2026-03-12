# dsl/blocks/role.py
"""
Role Agent: Routes messages based on status strings.

A Role agent is a generalization of Split where:
- The function returns an arbitrary list of (message, status) pairs
- Status strings determine which outport each message goes to
- The number of output messages is independent of the number of outports

This is the primary building block for org-compiler-generated networks.
Students can also use Role directly when they need more flexibility than
Split provides.

Pedagogical ladder:
    Transform → Split → Role → Agent
    (increasing power and complexity)
"""

from __future__ import annotations
from typing import Callable, Any, Optional, List, Tuple
import traceback

from dsl.core import Agent, STOP


class Role(Agent):
    """
    Role agent: routes messages based on status strings.

    Single input, multiple outputs. The function returns either:
    (1) an arbitrary list of (message, status) pairs — each status maps
        to a specific output port, or
    (2) a list of messages without explicit status values — each is
        coerced to status "all", or
    (3) a single message (not a list) — treated as [(message, "all")], or
    (4) None — message is dropped.

    **Ports:**
    - Inports: ["in_"]
    - Outports: ["out_0", "out_1", ..., "out_{n-1}"]
      where n = len(statuses)

    **Status to Outport Mapping:**
    statuses=["interesting", "boring", "exhausted"] maps to:
        "interesting" → out_0
        "boring"      → out_1
        "exhausted"   → out_2

    **Function Contract:**
    fn(msg) must:
    - Take a single message argument
    - Return a list of (message, status) pairs, OR
    - Return a list of messages (coerced to [(msg, "all")]), OR
    - Return a single message (coerced to [(msg, "all")]), OR
    - Return None (message dropped)
    - Every status returned must be in the declared statuses list

    **Coercion Rules:**
    If fn returns a bare value (not a list of pairs):
        "some string"  →  [("some string", "all")]
        {"key": val}   →  [({"key": val}, "all")]
    If fn returns a list of non-pairs:
        [msg1, msg2]   →  [(msg1, "all"), (msg2, "all")]
    If fn returns None:
        message is dropped (not forwarded)

    **Differences from Split:**
    - Split: returns exactly num_outputs messages, positional mapping
    - Role: returns arbitrary number of (msg, status) pairs, status-driven mapping
    - Role function does not need to know how many outports exist

    **Examples:**

    Editorial classifier:
        >>> def editorial_review(article):
        ...     score = article["score"]
        ...     if score > 0.75 or score < 0.25:
        ...         return [(article, "interesting")]
        ...     else:
        ...         return [(article, "boring")]
        >>> editor = Role(
        ...     fn=editorial_review,
        ...     statuses=["interesting", "boring"],
        ...     name="editor"
        ... )

    Multiple outputs from one input:
        >>> def triage(report):
        ...     outputs = []
        ...     if report["severity"] == "critical":
        ...         outputs.append((report, "alert"))
        ...         outputs.append((report, "archive"))
        ...     else:
        ...         outputs.append((report, "archive"))
        ...     return outputs
        >>> triager = Role(
        ...     fn=triage,
        ...     statuses=["alert", "archive"],
        ...     name="triage"
        ... )

    Filter (return empty list or None):
        >>> def filter_noise(msg):
        ...     if msg["score"] < 0.1:
        ...         return []   # drop message
        ...     return [(msg, "signal")]
        >>> filter_role = Role(
        ...     fn=filter_noise,
        ...     statuses=["signal"],
        ...     name="noise_filter"
        ... )
    """

    def __init__(
        self,
        *,
        fn: Callable[[Any], List[Tuple[Any, str]]],
        statuses: List[str],
        name: str
    ):
        """
        Initialize Role agent.

        Args:
            fn: Callable that processes messages.
                Signature: fn(msg) -> List[Tuple[msg, status_str]]
                Returns arbitrary list of (message, status) pairs,
                or a bare value (coerced to [(value, "all")]),
                or None (message dropped).
            statuses: Ordered list of valid status strings.
                Each unique string maps to one outport.
                statuses[0] → out_0, statuses[1] → out_1, etc.
                Every status returned by fn at runtime must appear here.
            name: Unique name for this agent (REQUIRED)

        Raises:
            TypeError: If fn is not callable
            ValueError: If statuses is empty or contains duplicates
        """
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

        # Map status strings to outport names
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

        Calls fn(msg) to get list of (message, status) pairs.
        Sends each message to the outport corresponding to its status.

        Coercion:
            None        → message dropped
            bare value  → [(value, "all")]
            [v1, v2]    → [(v1, "all"), (v2, "all")]
        """
        while True:
            msg = self.recv("in_")

            if msg is STOP:
                self.broadcast_stop()
                return

            try:
                results = self._fn(msg)

                # None means drop the message
                if results is None:
                    continue

                # Coerce bare value → [(value, "all")]
                if not isinstance(results, (list, tuple)):
                    results = [(results, "all")]
                # Coerce list of non-pairs → [(item, "all"), ...]
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
                self.broadcast_stop()
                return

    def __repr__(self) -> str:
        fn_name = getattr(self._fn, "__name__", repr(self._fn))
        return (
            f"<Role name={self.name} fn={fn_name} "
            f"statuses={self.statuses}>"
        )

    def __str__(self) -> str:
        return f"Role({self.statuses})"
