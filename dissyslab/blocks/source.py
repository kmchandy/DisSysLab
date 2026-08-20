# dissyslab/blocks/source.py
"""
Source Agent: Repeatedly calls a function to generate messages.

Sources have no inputs and generate data by calling fn() repeatedly until
it returns None. When exhausted, the source sends a termination message to
os_agent with its final sent counts. Termination is detected by os_agent —
sources do not send STOP signals.

Stateful sources
================

A Source may carry mutable state. Pass an ``initial_state`` dict at
construction; the runtime deep-copies it (so two Sources built from the
same template are independent) and passes the copy to ``fn`` as
``state=`` on every call. ``fn`` mutates ``state`` in place; subsequent
calls see the mutated state.

Backward compatibility: when ``state`` is not provided, ``fn`` is
called as ``fn(**params)`` — and generator functions still work.
When ``state`` is provided ``fn`` must be a regular callable, not a
generator function; use explicit state instead of ``yield`` for that
case.
"""

from __future__ import annotations
import inspect
import os
import traceback
import time
from copy import deepcopy
from typing import Any, Callable, Dict, Optional

from dissyslab.core import Agent


class Source(Agent):
    """
    Source Agent: Repeatedly calls a function to generate messages.

    **Ports:**
    - Inports: [] (no inputs - sources generate data)
    - Outports: ["out_"] (emits generated messages)

    **Function Requirements:**
    The fn callable must:
    - Return a message (any type) on each call
    - Return None when exhausted (no more messages)
    - Maintain its own state between calls (if needed)

    Generator functions are also accepted (when ``state`` is None) —
    Source wraps them automatically so that each call to fn() advances
    the generator by one step. ``params`` are passed to the generator
    function once when it is instantiated.

    **Stateless vs stateful:**
    When ``state`` is ``None`` (the default), ``fn`` is called as
    ``fn(**params)``. When ``state`` is a dict, ``fn`` receives that
    dict as the keyword argument ``state``; ``fn`` may mutate it in
    place and the mutations persist across calls. Generator functions
    are not supported when ``state`` is provided — use explicit state
    instead of ``yield``.

    The ``state`` argument is deep-copied at construction so building
    two Sources from the same initial-state dict produces two
    independent copies.

    **Termination:**
    When fn() returns None, the source sends a termination message to
    os_agent containing its final sent counts, then returns from run().
    os_agent uses this message to detect when all sources are done.

    **Optional Rate Limiting:**
    The interval parameter adds a delay between messages:
    - interval=0 (default): emit as fast as possible
    - interval=1.0: emit one message per second
    """

    def __init__(
        self,
        *,
        fn: Callable[..., Optional[Any]],
        name: Optional[str] = None,
        interval: float = 0,
        params: Optional[Dict[str, Any]] = None,
        state: Optional[Dict[str, Any]] = None,
        allow_empty: bool = False,
    ):
        if not callable(fn):
            raise TypeError(
                "Source fn must be callable with signature: "
                "fn() -> Optional[message]"
            )

        super().__init__(name=name, inports=[], outports=["out_"])

        params = params or {}
        self._params = params
        self._state: Optional[Dict[str, Any]] = (
            deepcopy(state) if state is not None else None
        )

        # Generator support is preserved only in the stateless case.
        # A generator carries its own state via ``yield``; combining
        # that with explicit ``state=`` would create two parallel
        # state mechanisms in the same fn.
        self._is_generator = False
        if inspect.isgeneratorfunction(fn):
            if state is not None:
                raise TypeError(
                    "Source fn must not be a generator function when "
                    "state= is provided. Use a regular callable that "
                    "mutates state instead of yielding."
                )
            _gen = fn(**params)
            self._fn = lambda: next(_gen, None)
            self._is_generator = True
        else:
            self._fn = fn

        self._interval = interval

        # A source that emits nothing across a whole run is almost
        # always misconfigured -- a path that does not exist, a feed
        # whose credentials expired. The office still terminates
        # correctly and reports success, so the mistake is invisible.
        # Network.run_network() treats it as an error unless the source
        # says empty is a legitimate outcome (an RSS feed with no new
        # items since the last poll, say).
        self.allow_empty = allow_empty

        # Set when run() catches an exception from fn. Distinct from
        # exhaustion: without it, "the source failed" and "the source
        # finished" are the same observable event.
        self.failure: Optional[str] = None

    @property
    def total_sent(self) -> int:
        """Messages this source emitted across the whole run."""
        return sum(self.sent.values())

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

    def _call_fn(self) -> Optional[Any]:
        """Invoke fn with the right arg shape for this source's mode."""
        if self._is_generator:
            return self._fn()                       # wrapper, zero-arg
        if self._state is None:
            return self._fn(**self._params)
        return self._fn(state=self._state, **self._params)

    def _send_termination(self) -> None:
        """Send final sent counts to os_agent on exhaustion or error.

        This is the only message a Source ever sends os_agent — it is
        never polled, because it is not sitting in ``recv`` where a poll
        could reach it. So this message carries the activity fields as
        well as the counts, and ``final`` is what tells os_agent to stop
        waiting for replies from a thread that has ended.

        A Source is *active* for its whole life and then final in one
        step; there is no state in which it is idle but still running.
        That is why it does not override ``is_idle`` — this message is
        the entire report.
        """
        self.send_os({
            "agent":    self.name,
            "sent":     dict(self.sent),
            "received": {},
            "idle":     True,
            "final":    True,
        })

    def run(self) -> None:
        """
        Main processing loop for the Source agent.

        Repeatedly calls fn to get messages and emits them. When fn
        returns None or an exception occurs, sends termination message
        to os_agent and returns.

        v1.6: between iterations, poll for OS messages
        (_Checkpoint, _PrepareRecover, _StartRecover). When the
        agent is in RECOVER_WAITING, block until _StartRecover
        releases the barrier. When self.os_q is None (the Source
        is being used outside a framework Network — e.g. in unit
        tests), the OS polling is skipped.
        """
        from dissyslab.core import _SnapshotState
        try:
            while True:
                # v1.6: poll OS messages between emission iterations.
                if self.os_q is not None:
                    self._poll_os(blocking=False)
                    while self._snapshot_state == _SnapshotState.RECOVER_WAITING:
                        self._poll_os(blocking=True, timeout=1.0)

                msg = self._call_fn()

                # None means the source is exhausted
                if msg is None:
                    self._send_termination()
                    return

                self.send(msg, "out_")

                if self._interval > 0:
                    time.sleep(self._interval)

        except Exception as e:
            # Record before terminating. The termination message still
            # has to go out or os_agent waits forever for a source that
            # is never coming back -- but sending it is what used to
            # make a crashed source indistinguishable from a finished
            # one, so the whole office reported success. run_network()
            # reads self.failure afterwards and raises.
            self.failure = f"{type(e).__name__}: {e}"
            print(f"[Source '{self.name}'] {type(e).__name__}: {e}")
            # The traceback is for whoever is debugging the framework,
            # not for the student who mistyped a path. Same convention
            # as the CLI's error mapper.
            if os.environ.get("DSL_DEBUG"):
                print(traceback.format_exc())
            self._send_termination()

    # v1.6: save_state and load_state delegate to the wrapped
    # callable's owner if it provides them. This lets source-class
    # authors (e.g. CSVPointsSource in dissyslab/components/sources/)
    # define their state cursor on their own object — the framework
    # picks it up automatically when a snapshot is taken or restored.
    def save_state(self):
        owner = getattr(self._fn, "__self__", None)
        if owner is not None and hasattr(owner, "save_state"):
            return {"owner_state": owner.save_state()}
        if self._state is None:
            return {}
        # Convention: keys starting with "_" are transient and not
        # checkpointed. The rest is the source's persistent state.
        return {
            k: v
            for k, v in self._state.items()
            if not k.startswith("_")
        }

    def load_state(self, state):
        owner = getattr(self._fn, "__self__", None)
        if owner is not None and hasattr(owner, "load_state"):
            if isinstance(state, dict) and "owner_state" in state:
                owner.load_state(state["owner_state"])
            return
        if isinstance(state, dict) and self._state is not None:
            # Reset persistent keys, then merge in the saved values.
            for k in list(self._state.keys()):
                if not k.startswith("_"):
                    del self._state[k]
            self._state.update(state)

    def __repr__(self) -> str:
        fn_name = getattr(self._fn, "__name__", repr(self._fn))
        interval_str = f", interval={self._interval}" if self._interval > 0 else ""
        return f"<Source name={self.name} fn={fn_name}{interval_str}>"

    def __str__(self) -> str:
        return "Source"
