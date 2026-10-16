"""The two agents the framework inserts into a network by itself.

A connection joins one outbox to one inbox. When an office connects one
outbox to several inboxes (fan-out, ``a -> b, c``), or several outboxes
to one inbox (fan-in, ``a, b -> c``), the network inserts one of these
agents to do the copying or merging:

- ``Broadcast`` receives on one inbox and sends a separate deep copy of
  each message to each of its outboxes, so that every receiver gets its
  own copy (spec section 8, step 3).
- ``MergeAsynch`` receives on several inboxes and forwards each message
  to its one outbox as soon as it arrives. The order between inboxes is
  whatever order the messages happen to arrive in; the order within one
  inbox is kept (channels are FIFO, spec section 2).

``Network`` names them ``broadcast_<i>`` and ``merge_<i>``, which is how
they appear in a trace, and marks them ``framework_inserted = True`` so
the run summary can leave them out. ``dsl draw`` shows the office as
written, without them.

Termination is not handled here. The termination detector
(``dissyslab.os_agent``) sends ``_Shutdown`` on every inbox when the
network has finished, and ``Agent.recv`` turns it into
``_ShutdownSignal``, which ends the agent's loop.
"""

from __future__ import annotations

import copy
import threading

from dissyslab.runtime.agent import Agent
from dissyslab.runtime.messages import _ShutdownSignal


class Broadcast(Agent):
    """Copy each message to every outbox (fan-out).

    Ports: one inbox ``in_``; outboxes ``out_0`` .. ``out_{n-1}``.
    Each outbox gets its own deep copy, so no receiver can change a
    message another receiver is reading.
    """

    def __init__(self, *, num_outputs: int, name: str | None = None) -> None:
        if num_outputs < 1:
            raise ValueError(f"Broadcast requires at least 1 output, got {num_outputs}")
        outports = [f"out_{i}" for i in range(num_outputs)]
        super().__init__(name=name, inports=["in_"], outports=outports)
        self.num_outputs = num_outputs
        # Set to True by Network when it inserts this agent itself.
        self.framework_inserted = False

    @property
    def default_inport(self) -> str:
        """The inbox a bare connection arrives at."""
        return "in_"

    @property
    def default_outport(self) -> str | None:
        """None: with several outboxes, a bare connection is ambiguous."""
        return None

    def run(self) -> None:
        """Receive one message, send a copy to each outbox, repeat."""
        while True:
            msg = self.recv("in_")
            for i in range(self.num_outputs):
                self.send(copy.deepcopy(msg), f"out_{i}")

    def __repr__(self) -> str:
        return f"<Broadcast name={self.name} outputs={self.num_outputs}>"

    def __str__(self) -> str:
        return f"Broadcast({self.num_outputs} outputs)"


class MergeAsynch(Agent):
    """Forward messages from several inboxes to one outbox (fan-in).

    Ports: inboxes ``in_0`` .. ``in_{n-1}``; one outbox ``out_``.
    One thread per inbox forwards each message as soon as it arrives, so
    the order between inboxes is not determined.
    """

    def __init__(self, *, num_inputs: int, name: str | None = None) -> None:
        if num_inputs < 1:
            raise ValueError(f"MergeAsynch requires at least 1 input, got {num_inputs}")
        inports = [f"in_{i}" for i in range(num_inputs)]
        super().__init__(name=name, inports=inports, outports=["out_"])
        self.num_inputs = num_inputs
        # Set to True by Network when it inserts this agent itself.
        self.framework_inserted = False
        # This is the only agent with several threads. They share the
        # checkpoint bookkeeping in Agent, which guards it with
        # ``self._snapshot_lock``; every other agent has one thread and
        # keeps Agent's no-op lock. Here it must be a real lock.
        self._snapshot_lock = threading.Lock()
        #: Messages received and already forwarded (see is_idle).
        self._forwarded = 0
        self._count_lock = threading.Lock()

    @property
    def default_inport(self) -> str | None:
        """None: with several inboxes, a bare connection is ambiguous."""
        return None

    @property
    def default_outport(self) -> str:
        """The outbox a bare connection leaves from."""
        return "out_"

    def _worker(self, port: str) -> None:
        """Forward messages from one inbox until the network shuts down."""
        try:
            while True:
                msg = self.recv(port)
                try:
                    self.send(msg, "out_")
                finally:
                    with self._count_lock:
                        self._forwarded += 1
        except _ShutdownSignal:
            pass  # the termination detector has ended the run

    def is_idle(self) -> bool:
        """Idle only when every message received has been forwarded.

        One thread can answer the termination detector's poll while
        another holds a message it has received but not yet sent. If that
        answer were "idle", every channel would look balanced and the
        detector could end the run with the message lost (found 16 Oct
        2026 by slowing a worker down; it lost one message in three).
        ``recv`` counts a message before returning it and ``_forwarded``
        counts it after ``send``, so a message in between makes this False.
        """
        return self._forwarded >= sum(self.received.values())

    def run(self) -> None:
        """Start one forwarding thread per inbox and wait for all of them."""
        threads = []
        for port in self.inports:
            thread = threading.Thread(
                target=self._worker, args=(port,), name=f"merge_worker_{port}", daemon=False
            )
            thread.start()
            threads.append(thread)
        for thread in threads:
            thread.join()

    def __repr__(self) -> str:
        return f"<MergeAsynch name={self.name} inputs={self.num_inputs}>"

    def __str__(self) -> str:
        return f"MergeAsynch({self.num_inputs} inputs)"
