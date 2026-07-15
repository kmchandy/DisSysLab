# dissyslab/blocks/coordinator.py
"""
Coordinator Agent: the base class for controlled multi-inport agents.

A Transform has one input and one output: every step it reads its one
inbox, applies ``fn`` to the message, and sends the result. A
Coordinator generalises this to agents with **several inboxes and
several outboxes** whose behaviour is *controlled by their own state*.

Each step a Coordinator:

1. chooses **which inbox to read** — ``get_inport(state)`` returns an
   inport name;
2. **reads** that inbox (a blocking ``recv``);
3. runs a **step function** — ``fn(msg, state=state, inport=inport,
   **params)`` — which may mutate ``state`` and returns the messages to
   send, as a list of ``(outport, message)`` pairs (or ``None`` to send
   nothing);
4. **sends** each of those messages.

This one shape is the common structure of the *deterministic*
coordination primitives, which are written as Coordinator subclasses:

- ``select``      — ask-and-wait: ``get_inport`` returns the inbox the
                    state points to (send a request, then read the reply).
- ``merge_synch`` — join: ``get_inport`` cycles through the not-yet-filled
                    inboxes; ``fn`` files each message into a slot and
                    emits the combined result once every slot is full.
- ``gate``        — one-at-a-time: ``get_inport`` alternates between the
                    data inbox and the "done" inbox.
- ``router``      — the dual: one inbox, but ``fn`` chooses the outbox.

Why this base is exactly the *deterministic* primitives
=======================================================

An agent that **blocks on an inbox it chose from its own state** is a
determinate (Kahn) process: its outputs depend only on its inputs and
its state, never on arrival timing. That is precisely why ``get_inport``
is a function of ``state`` alone. ``fair_merge`` (MergeAsynch) — "read
whichever inbox is ready first" — cannot be written this way, and so is
**not** a Coordinator. It is the single nondeterministic primitive, kept
as its own multi-threaded agent. The Coordinator base draws the line
between determinate coordination and the one nondeterministic case in
the class hierarchy itself.

The step function
=================

``fn`` is called once per received message. Unlike a Transform's ``fn``
(which returns a single value sent to ``out_``), a Coordinator's ``fn``
returns **a list of ``(outport, message)`` pairs** — possibly empty, so
an agent can consume a message without emitting (a join swallowing the
first of a pair), and can emit on a chosen outbox (a router). It also
receives ``inport``: the inbox the message came from. That argument is
load-bearing — a join needs it to know which slot to fill, a gate needs
it to tell a data message from a "done" message.

Stateless vs stateful
=====================

Like Transform, when ``state`` is ``None`` (the default) ``fn`` is
called as ``fn(msg, inport=inport, **params)``; when ``state`` is a
dict, ``fn`` receives it as the keyword argument ``state`` and may
mutate it in place. In practice a Coordinator is almost always stateful,
because ``get_inport`` and the join/gate logic are driven by state; the
``state`` dict is deep-copied at construction so two agents built from
the same template are independent.

Example — a two-inbox join (the shape of ``merge_synch``)::

    def join_step(msg, state, inport):
        state["slots"][inport] = msg
        if len(state["slots"]) < 2:
            return None                       # wait for the other inbox
        pair = dict(state["slots"])
        state["slots"] = {}                   # reset for the next round
        return [("out_", pair)]

    def next_inport(state):
        # read whichever inbox we have not yet filled this round
        return "in_1" if "in_0" in state["slots"] else "in_0"

    join = Coordinator(
        fn=join_step,
        get_inport=next_inport,
        inports=["in_0", "in_1"],
        state={"slots": {}},
        name="join",
    )

Subclasses (``select``, ``merge_synch``, ``gate``, ``router``) usually
override the ``get_inport``/``fn`` behaviour by overriding the
``_get_inport`` and ``_step`` methods instead of passing callables — the
callable form above is the equivalent for one-off, in-line agents.
"""

from __future__ import annotations
from copy import deepcopy
from typing import Any, Callable, Optional, Dict, List, Tuple
import traceback

from dissyslab.core import Agent


# A step returns the messages to send: a list of (outport, message)
# pairs. None and [] both mean "send nothing this step".
Sends = Optional[List[Tuple[str, Any]]]


class Coordinator(Agent):
    """
    Controlled multi-inport / multi-outport agent.

    Each step the agent chooses an inport (from its state), reads it,
    runs a step function, and sends that function's result. It is the
    base class for the deterministic coordination primitives
    (``select``, ``merge_synch``, ``gate``, ``router``).

    **Ports:**
    - Inports: whatever is passed as ``inports`` (at least one).
    - Outports: whatever is passed as ``outports`` (default ``["out_"]``).

    **Per-step behaviour:**
    1. ``inport = self._get_inport(state)`` — which inbox to read.
    2. ``msg = self.recv(inport)`` — blocking read.
    3. ``sends = self._step(msg, state, inport)`` — a list of
       ``(outport, message)`` pairs, or ``None``.
    4. ``self.send(message, outport)`` for each pair.

    **Choosing the inport (``get_inport``):**
    ``get_inport(state)`` depends on ``state`` alone. This is what makes
    a Coordinator a determinate (Kahn) process. Provide it either as the
    ``get_inport=`` constructor argument or by overriding
    ``_get_inport`` in a subclass. If neither is provided and the agent
    has exactly one data inport, that inport is used every step.

    **The step function (``fn``):**
    ``fn(msg, state=state, inport=inport, **params)`` (or
    ``fn(msg, inport=inport, **params)`` when ``state`` is ``None``). It
    returns a list of ``(outport, message)`` pairs to send, or ``None``
    to send nothing. Provide it as the ``fn=`` constructor argument or
    by overriding ``_step`` in a subclass.

    **Termination:**
    Detected by os_agent and signalled via _Shutdown, which recv()
    turns into _ShutdownSignal to unwind run(). No explicit STOP
    handling needed.

    **Checkpointing:**
    The ``state`` dict is saved and restored across snapshots, so the
    coordination state (a join's half-filled slots, a gate's "busy"
    flag) survives a checkpoint and a replay.
    """

    def __init__(
        self,
        *,
        inports: List[str],
        outports: Optional[List[str]] = None,
        fn: Optional[Callable[..., Sends]] = None,
        get_inport: Optional[Callable[[Optional[Dict[str, Any]]], str]] = None,
        name: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
        state: Optional[Dict[str, Any]] = None,
    ):
        if not inports:
            raise ValueError(
                "Coordinator requires at least one inport; got "
                f"{inports!r}"
            )
        if fn is not None and not callable(fn):
            raise TypeError(
                f"Coordinator fn must be callable, got {type(fn).__name__}"
            )
        if get_inport is not None and not callable(get_inport):
            raise TypeError(
                "Coordinator get_inport must be callable, got "
                f"{type(get_inport).__name__}"
            )

        super().__init__(
            name=name,
            inports=list(inports),
            outports=list(outports) if outports is not None else ["out_"],
        )
        self._fn = fn
        self._get_inport_fn = get_inport
        self._params = params or {}
        # Deep-copy so two Coordinators built from the same initial-state
        # dict are independent. ``None`` means "stateless" — ``fn`` is
        # then called as ``fn(msg, inport=inport, **params)``.
        self._state: Optional[Dict[str, Any]] = (
            deepcopy(state) if state is not None else None
        )

    # ========== State ==========

    @property
    def state(self) -> Optional[Dict[str, Any]]:
        """The agent's mutable state (or ``None`` if stateless).

        Exposed for inspection and checkpointing. Mutating the returned
        dict mutates the agent's live state — handle with care.
        """
        return self._state

    def save_state(self) -> Any:
        """Capture the coordination state for a snapshot.

        The ``state`` dict is the whole of a Coordinator's user state,
        so persisting it is enough for a join's half-filled slots or a
        gate's "busy" flag to survive a checkpoint and replay. ``state``
        must be pickle-safe (the general save_state contract).
        """
        return {"state": self._state}

    def load_state(self, saved: Any) -> None:
        """Restore the coordination state saved by ``save_state``."""
        if isinstance(saved, dict) and "state" in saved:
            self._state = saved["state"]

    # ========== Policy + step (override in subclasses) ==========

    def _get_inport(self, state: Optional[Dict[str, Any]]) -> str:
        """Return the inport to read this step.

        Uses the ``get_inport=`` callable if one was supplied; otherwise
        falls back to the single data inport. Subclasses (``select``,
        ``merge_synch``, ``gate``) override this with their own policy.
        The choice must depend on ``state`` alone — that is what keeps a
        Coordinator determinate.
        """
        if self._get_inport_fn is not None:
            return self._get_inport_fn(state)
        data_inports = [p for p in self.inports
                        if p != Agent._OS_PORT_NAME]
        if len(data_inports) == 1:
            return data_inports[0]
        raise NotImplementedError(
            f"Coordinator '{self.name}' has {len(data_inports)} data "
            "inports; supply get_inport= or override _get_inport() to "
            "choose which inbox to read each step."
        )

    def _step(
        self,
        msg: Any,
        state: Optional[Dict[str, Any]],
        inport: str,
    ) -> Sends:
        """Process one received message; return the messages to send.

        Calls the ``fn=`` callable if one was supplied. Subclasses may
        override this instead of passing ``fn``. Returns a list of
        ``(outport, message)`` pairs, or ``None`` to send nothing.
        """
        if self._fn is None:
            raise NotImplementedError(
                f"Coordinator '{self.name}' has no step function; supply "
                "fn= or override _step()."
            )
        if state is None:
            return self._fn(msg, inport=inport, **self._params)
        return self._fn(msg, state=state, inport=inport, **self._params)

    # ========== Run loop ==========

    def run(self) -> None:
        """
        Loop: choose an inbox, read it, run the step, send the result.

        recv() intercepts _Shutdown and raises _ShutdownSignal, which
        unwinds this loop cleanly. An exception raised by the step
        function is reported and stops this agent (matching Transform).
        """
        while True:
            inport = self._get_inport(self._state)
            if inport not in self.inports:
                raise ValueError(
                    f"Coordinator '{self.name}' get_inport returned "
                    f"'{inport}', which is not one of its inports "
                    f"{self.inports}."
                )
            msg = self.recv(inport)
            try:
                sends = self._step(msg, self._state, inport)
            except Exception as e:
                print(f"[Coordinator '{self.name}'] Error in step: {e}")
                print(traceback.format_exc())
                return
            for outport, out_msg in (sends or []):
                self.send(out_msg, outport)

    def __repr__(self) -> str:
        fn_name = getattr(self._fn, "__name__", repr(self._fn))
        return (
            f"<Coordinator name={self.name} inports={self.inports} "
            f"outports={self.outports} fn={fn_name}>"
        )

    def __str__(self) -> str:
        return "Coordinator"
