# dissyslab/blocks/transform.py
"""
Transform Agent: Applies a function to transform messages.

Transforms have one input and one output. They process each message by
calling fn(msg, **params) — or fn(msg, state=state, **params) when state
is provided — and sending the result downstream. Termination is signaled
by os_agent via _Shutdown, handled transparently by recv().

Stateful transforms
===================

A Transform may carry mutable state. Pass an ``initial_state`` dict at
construction; the runtime deep-copies it (so two Transforms built from
the same template are independent) and passes the copy to ``fn`` as
``state=`` on every call. ``fn`` mutates ``state`` in place; subsequent
messages see the mutated state.

Backward compatibility: when ``state`` is not provided, ``fn`` is
called as ``fn(msg, **params)`` — the long-standing contract. Existing
stateless transforms keep working unchanged.

Example::

    def deduplicator(msg, state, by="url"):
        key = msg[by]
        if key in state["seen"]:
            return None             # drop duplicates
        state["seen"].add(key)
        return msg

    sasha = Transform(
        fn=deduplicator,
        params={"by": "url"},
        state={"seen": set()},
        name="Sasha",
    )
"""

from __future__ import annotations
from copy import deepcopy
from typing import Any, Callable, Optional, Dict
import traceback

from dissyslab.core import Agent


class Transform(Agent):
    """
    Transform agent: applies a function to each message.

    Single input, single output. Processes each message by calling
    ``fn(msg, **params)`` — or ``fn(msg, state=state, **params)`` when
    ``state`` is provided at construction — and sending the result.

    **Ports:**
    - Inports: ["in_"]
    - Outports: ["out_"]

    **Termination:**
    Termination is detected by os_agent and signaled via _Shutdown,
    which recv() handles transparently by raising _ShutdownSignal.
    No explicit STOP handling needed.

    **Stateless vs stateful:**
    When ``state`` is ``None`` (the default), ``fn`` is called as
    ``fn(msg, **params)``. When ``state`` is a dict, ``fn`` receives
    that dict as the keyword argument ``state``; ``fn`` may mutate it
    in place and the mutations persist across calls.

    The ``state`` argument is deep-copied at construction so building
    two Transforms from the same initial-state dict produces two
    independent copies.
    """

    def __init__(
        self,
        *,
        fn: Callable[..., Optional[Any]],
        name: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
        state: Optional[Dict[str, Any]] = None,
    ):
        if not callable(fn):
            raise TypeError(
                f"Transform fn must be callable, got {type(fn).__name__}"
            )

        super().__init__(name=name, inports=["in_"], outports=["out_"])
        self._fn = fn
        self._params = params or {}
        # Deep-copy so two Transforms built from the same template are
        # independent. ``None`` means "stateless" — preserves the
        # original fn(msg, **params) contract.
        self._state: Optional[Dict[str, Any]] = (
            deepcopy(state) if state is not None else None
        )

    @property
    def default_inport(self) -> str:
        """Default input port for edge syntax."""
        return "in_"

    @property
    def default_outport(self) -> str:
        """Default output port for edge syntax."""
        return "out_"

    @property
    def state(self) -> Optional[Dict[str, Any]]:
        """The agent's mutable state (or ``None`` if stateless).

        Exposed for inspection and checkpointing. Mutating the returned
        dict mutates the agent's live state — handle with care.
        """
        return self._state

    def run(self) -> None:
        """
        Process messages until _Shutdown is received.

        recv() intercepts _Shutdown and raises _ShutdownSignal,
        which unwinds this loop cleanly.
        """
        while True:
            msg = self.recv("in_")
            try:
                if self._state is None:
                    result = self._fn(msg, **self._params)
                else:
                    result = self._fn(
                        msg, state=self._state, **self._params
                    )
            except Exception as e:
                print(f"[Transform '{self.name}'] Error in fn: {e}", flush=True)
                print(traceback.format_exc(), flush=True)
                return
            self.send(result, "out_")

    def __repr__(self) -> str:
        fn_name = getattr(self._fn, "__name__", repr(self._fn))
        return f"<Transform name={self.name} fn={fn_name}>"

    def __str__(self) -> str:
        return "Transform"
