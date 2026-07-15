# dissyslab/blocks/select.py
"""
select: read whichever inport the state points to, as a Coordinator
subclass.

A ``select`` worker keeps a pointer, ``state["next"]``, to the inport it
should read next, and updates that pointer as messages arrive. Use it
for **ask-and-wait** (send a request, then wait for the reply) and for
taking inputs in a **set order** rather than "whoever arrives first."

``select`` is the most general of the deterministic coordination
primitives: ``merge_synch`` and ``gate`` have fixed inport-selection
policies, whereas ``select`` lets the office's step function drive the
policy through ``state["next"]``. Because the next inport is still a
function of state alone, ``select`` is determinate.

The step function has the Coordinator signature and, in addition to
returning its sends, sets ``state["next"]`` to the inport to read next::

    # ask-and-wait: read a job on in_, ask the keeper, wait for the reply
    def step(msg, state, inport):
        if inport == "in_":
            state["pending"] = msg
            state["next"] = "reply"                 # now wait for the answer
            return [("request", make_query(msg))]
        # inport == "reply"
        state["next"] = "in_"                        # back to reading jobs
        return [("out_", combine(state.pop("pending"), msg))]

    head = Select(
        inports=["in_", "reply"],
        outports=["request", "out_"],
        fn=step,
        start="in_",
        name="head",
    )
"""

from __future__ import annotations
from typing import Any, Callable, Dict, List, Optional

from dissyslab.core import Agent
from dissyslab.blocks.coordinator import Coordinator, Sends


class Select(Coordinator):
    """
    Reads whichever inport ``state["next"]`` points to.

    **Ports:** whatever ``inports`` / ``outports`` the office declares.

    **State:** an office-defined dict that must carry ``state["next"]``
    — the name of the inport to read on the next step. The step function
    (``fn``) updates it. ``start`` sets its initial value (default: the
    first inport).

    **Step function:** the Coordinator contract —
    ``fn(msg, state=state, inport=inport, **params)`` returning a list of
    ``(outport, message)`` pairs — with the added responsibility of
    setting ``state["next"]``.
    """

    def __init__(
        self,
        *,
        inports: List[str],
        fn: Callable[..., Sends],
        outports: Optional[List[str]] = None,
        name: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
        state: Optional[Dict[str, Any]] = None,
        start: Optional[str] = None,
    ):
        state = dict(state) if state is not None else {}
        if "next" not in state:
            state["next"] = start if start is not None else inports[0]
        super().__init__(
            inports=inports,
            outports=outports,
            fn=fn,
            name=name,
            params=params,
            state=state,
        )

    def _get_inport(self, state: dict) -> str:
        """Read the inport the state points to."""
        nxt = state.get("next")
        if nxt is not None:
            return nxt
        # No pointer set — fall back to the first data inport.
        return next(p for p in self.inports if p != Agent._OS_PORT_NAME)

    def __str__(self) -> str:
        return "Select"
