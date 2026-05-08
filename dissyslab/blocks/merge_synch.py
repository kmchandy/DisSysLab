# dissyslab/blocks/merge_synch.py
"""
Merge Agents: Combine multiple inputs into single output.

MergeSynch: Synchronous merge in round-robin order (use sparingly).
For most use cases, prefer MergeAsynch in fanin.py.

Termination is signaled by os_agent via _Shutdown, handled transparently
by recv(). No explicit STOP handling needed.
"""

from __future__ import annotations
from typing import List, Optional

from dissyslab.core import Agent


class MergeSynch(Agent):
    """
    MergeSynch agent: synchronously combine inputs in round-robin order.

    **WARNING: Use only when deterministic ordering is required AND all
    inputs produce messages at similar rates. For most use cases, prefer
    MergeAsynch.**

    The constructor takes a list of port names. The agent's `run()` loop
    receives one message from each named inport in order, packages them
    into a dict keyed by inport name, and emits the dict on `out_`.

    **Ports:**
    - Inports: the names you pass in via ``inports=...``.
    - Outports: ``["out_"]`` — single output, follows the framework's
      single-port convention.

    **Output shape:**
    Each cycle emits a single ``dict`` of the form::

        {inport_name: message_received_on_that_inport, ...}

    so a downstream agent can unpack by key. For four parallel
    extractors you'd typically pass
    ``inports=["in_entity", "in_severity", "in_topic", "in_geo"]``
    and the merged output would be a dict with those four keys.

    **Termination:**
    Termination is detected by os_agent and signaled via _Shutdown,
    which recv() handles transparently by raising _ShutdownSignal.
    """

    def __init__(
        self,
        *,
        inports: List[str],
        name: Optional[str] = None,
    ) -> None:
        if not inports:
            raise ValueError(
                "MergeSynch requires at least one inport"
            )
        if len(set(inports)) != len(inports):
            raise ValueError(
                f"MergeSynch inports must be unique, got {list(inports)}"
            )
        super().__init__(
            name=name, inports=list(inports), outports=["out_"]
        )
        self.num_inputs = len(inports)

    @property
    def default_inport(self) -> Optional[str]:
        """No default input (multiple inputs — ambiguous)."""
        return None

    @property
    def default_outport(self) -> str:
        """Default output port for edge syntax."""
        return "out_"

    def run(self) -> None:
        """
        Synchronous merge loop: collect one message from each inport
        in order, emit them as a single dict keyed by port name.

        recv() intercepts _Shutdown and raises _ShutdownSignal,
        which unwinds this loop cleanly.
        """
        while True:
            batch = {p: self.recv(p) for p in self.inports}
            self.send(batch, "out_")

    def __repr__(self) -> str:
        return (
            f"<MergeSynch name={self.name} "
            f"inports={list(self.inports)}>"
        )

    def __str__(self) -> str:
        return f"MergeSynch({self.num_inputs} inports)"
