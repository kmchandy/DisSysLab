# dissyslab/blocks/sink.py
"""
Sink Agent: Consumes messages for side effects.

Sinks have one input and no outputs. They are terminal nodes that call
fn(msg, **params) — or fn(msg, state=state, **params) when state is
provided — for each message to perform side effects like printing,
saving, or collecting. Termination is signaled by os_agent via
_Shutdown, which is handled transparently by recv().

Stateful sinks
==============

A Sink may carry mutable state. Pass an ``initial_state`` dict at
construction; the runtime deep-copies it (so two Sinks built from the
same template are independent) and passes the copy to ``fn`` as
``state=`` on every call. ``fn`` mutates ``state`` in place; subsequent
messages see the mutated state.

Backward compatibility: when ``state`` is not provided, ``fn`` is
called as ``fn(msg, **params)`` — the long-standing contract.
"""

from __future__ import annotations
from copy import deepcopy
from typing import Any, Callable, Dict, Optional
import traceback

from dissyslab.core import Agent


class Sink(Agent):
    """
    Sink agent: consumes messages for side effects.

    Single input, no outputs. Terminal node that calls
    ``fn(msg, **params)`` — or ``fn(msg, state=state, **params)`` when
    ``state`` is provided — for each message. Used for actions like
    printing, saving, or sending.

    **Ports:**
    - Inports: ["in_"]
    - Outports: [] (no outputs)

    **Stateless vs stateful:**
    When ``state`` is ``None`` (the default), ``fn`` is called as
    ``fn(msg, **params)``. When ``state`` is a dict, ``fn`` receives
    that dict as the keyword argument ``state``; ``fn`` may mutate it
    in place and the mutations persist across messages.

    The ``state`` argument is deep-copied at construction so building
    two Sinks from the same initial-state dict produces two independent
    copies.

    **Termination:**
    Termination is detected by os_agent and signaled via _Shutdown,
    which recv() handles transparently by raising _ShutdownSignal.
    No explicit STOP handling needed.
    """

    def __init__(
        self,
        *,
        fn: Callable[..., None],
        name: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
        state: Optional[Dict[str, Any]] = None,
    ):
        if not callable(fn):
            raise TypeError(
                f"Sink fn must be callable, got {type(fn).__name__}"
            )

        super().__init__(name=name, inports=["in_"], outports=[])
        self._fn = fn
        self._params = params or {}
        self._state: Optional[Dict[str, Any]] = (
            deepcopy(state) if state is not None else None
        )

    @property
    def default_inport(self) -> str:
        """Default input port for edge syntax."""
        return "in_"

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
                    self._fn(msg, **self._params)
                else:
                    self._fn(msg, state=self._state, **self._params)
            except Exception as e:
                print(f"[Sink '{self.name}'] Error in fn: {e}")
                print(traceback.format_exc())
                return

    def __repr__(self) -> str:
        fn_name = getattr(self._fn, "__name__", repr(self._fn))
        return f"<Sink name={self.name} fn={fn_name}>"

    def __str__(self) -> str:
        return "Sink"
