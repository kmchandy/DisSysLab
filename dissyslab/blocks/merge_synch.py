# dissyslab/blocks/merge_synch.py
"""
merge_synch: a synchronizing join, as a Coordinator subclass.

Waits for one message on each of its inports, combines them into a
single message, and emits it — then starts the next round. Use when a
worker needs several inputs *for the same item* (for example, two
weather services' forecasts for the same day).

Contrast with ``fair_merge`` (MergeAsynch), which forwards whichever
message arrives first and keeps no per-round state. ``merge_synch`` is
determinate: it reads its inports in a fixed order chosen from its own
state, so its output does not depend on arrival timing.

The coordination — wait for one on each inport, then emit — is fixed and
trusted. The only thing an office may customise is how the collected
messages are combined into the emitted message, via ``combine``.

Example::

    join = MergeSynch(num_inputs=2, name="join")
    # emits [msg_on_in_0, msg_on_in_1] once both have arrived

    def pair(msgs):                      # msgs is [in_0's msg, in_1's msg]
        a, b = msgs
        return {"day": a["day"],
                "forecasts": {a["service"]: a["forecast"],
                              b["service"]: b["forecast"]}}

    join = MergeSynch(num_inputs=2, combine=pair, name="join")
"""

from __future__ import annotations
from typing import Any, Callable, List, Optional

from dissyslab.core import Agent
from dissyslab.blocks.coordinator import Coordinator, Sends


class MergeSynch(Coordinator):
    """
    Synchronizing join. Waits for one message on each inport, combines
    them, emits one message, repeats.

    **Ports:**
    - Inports: ``in_0 … in_{num_inputs-1}`` (or an explicit ``inports``
      list).
    - Outports: ``["out_"]``.

    **Combine:**
    By default the emitted message is the list of the round's messages
    in inport order. Pass ``combine(messages)`` to produce a custom
    joined message; ``messages`` is that ordered list.
    """

    def __init__(
        self,
        *,
        num_inputs: Optional[int] = None,
        inports: Optional[List[str]] = None,
        combine: Optional[Callable[[List[Any]], Any]] = None,
        name: Optional[str] = None,
    ):
        if inports is None:
            if num_inputs is None or num_inputs < 1:
                raise ValueError(
                    "MergeSynch needs num_inputs >= 1 or an explicit "
                    f"inports list; got num_inputs={num_inputs!r}, "
                    f"inports={inports!r}"
                )
            inports = [f"in_{i}" for i in range(num_inputs)]
        if combine is not None and not callable(combine):
            raise TypeError(
                f"MergeSynch combine must be callable, got "
                f"{type(combine).__name__}"
            )
        super().__init__(
            inports=inports,
            outports=["out_"],
            name=name,
            state={"slots": {}},
        )
        self._combine = combine

    def _data_inports(self) -> List[str]:
        return [p for p in self.inports if p != Agent._OS_PORT_NAME]

    def _get_inport(self, state: dict) -> str:
        """Read the next inport (in order) that this round has not yet
        filled."""
        for p in self._data_inports():
            if p not in state["slots"]:
                return p
        # All filled — cannot normally happen, because _step resets
        # slots the moment the round completes. Fall back to the first.
        return self._data_inports()[0]

    def _step(self, msg: Any, state: dict, inport: str) -> Sends:
        """File the message into this round's slot; emit the combined
        message once every inport has been filled."""
        state["slots"][inport] = msg
        data = self._data_inports()
        if len(state["slots"]) < len(data):
            return None                      # still waiting for others
        ordered = [state["slots"][p] for p in data]
        state["slots"] = {}                  # reset for the next round
        out = self._combine(ordered) if self._combine else ordered
        return [("out_", out)]

    def __str__(self) -> str:
        return "MergeSynch"
