# dissyslab/blocks/gate.py
"""
gate: admit one item at a time, as a Coordinator subclass.

A gate forwards one item, then waits for a "done" signal before
admitting the next. Use when the office must finish one item before
starting the next — typically because some agent that *owns* shared
information is updated as part of handling each item, and its memory
must stay consistent.

The gate has two inports: the data inport it admits from (``in_``) and
the control inport the "done" signal arrives on (``done``). Its state is
a single ``busy`` flag, and that flag alone chooses which inport it
reads next — so the gate is determinate.

Wiring sketch::

    emails -> Gary(gate) -> Hana -> ... -> Mia
    Mia ..done..> Gary            # the last worker signals completion

Behaviour, each cycle:
1. not busy → read ``in_``, forward it on ``out_``, become busy;
2. busy → read ``done``, become not busy.
"""

from __future__ import annotations
from typing import Any, Dict, Optional

from dissyslab.blocks.coordinator import Coordinator, Sends


class Gate(Coordinator):
    """
    One-at-a-time gate.

    **Ports:**
    - Inports: ``["in_", "done"]`` — the item stream and the completion
      signal.
    - Outports: ``["out_"]`` — the admitted item.

    **State:** ``{"busy": bool}`` — whether an item is currently in
    flight. The flag alone decides which inport is read next.
    """

    def __init__(
        self,
        *,
        name: Optional[str] = None,
        in_port: str = "in_",
        done_port: str = "done",
        out_port: str = "out_",
    ):
        super().__init__(
            inports=[in_port, done_port],
            outports=[out_port],
            name=name,
            state={"busy": False},
        )
        self._in = in_port
        self._done = done_port
        self._out = out_port

    def _get_inport(self, state: dict) -> str:
        """Read ``done`` while an item is in flight, otherwise admit the
        next item from ``in_``."""
        return self._done if state["busy"] else self._in

    def _step(self, msg: Any, state: dict, inport: str) -> Sends:
        if inport == self._in:
            state["busy"] = True             # an item is now in flight
            return [(self._out, msg)]         # forward it
        # inport == self._done
        state["busy"] = False                 # released; admit the next
        return None

    def _termination_info(self) -> Dict[str, Any]:
        """Besides ``waiting_on``: while busy, the gate holds an admitted item.

        The termination detector starts its stall walk from agents that
        hold work (``OsAgent._find_stalls``): a gate waiting on ``done``
        that can never arrive has stalled everything behind it.
        """
        info = super()._termination_info()
        if self._state.get("busy"):
            info["holding"] = {"what": "an item it admitted, until done arrives",
                               "needs": [self._done]}
        return info

    def __str__(self) -> str:
        return "Gate"
