"""Agent: a named worker with inboxes and outboxes, running in its own thread.

Every agent in a running office is an ``Agent``: roles, routers,
coordinators, sources and sinks. An agent

- has named **inboxes** (``inports``) and **outboxes** (``outports``);
- runs its ``run`` method in its own thread;
- reads one message at a time with ``recv(inbox)``, which blocks until a
  message arrives;
- writes with ``send(msg, outbox)``, which never blocks.

The network (``dissyslab.network``) connects each outbox to an inbox by
giving both ends the same FIFO queue. That is the whole communication
model: no shared variables, no other channels.

**What the operating system adds.** ``Agent`` inherits from ``OsHooks``
(:mod:`dissyslab.runtime.os_hooks`), which holds everything the framework
does on the agent's thread without the role seeing it: answering the
termination detector, taking part in snapshots and recovery, and
tracing. ``send`` and ``recv`` below show each point where it steps in,
as one call to an ``_os_*`` method.

**Failures.** When an agent cannot handle one message (a role raised, a
model's reply did not fit), it calls ``report_failure`` and carries on
with the next message. The failure is counted, the first one is printed,
the run summary reports the total, and ``dsl run`` exits non-zero. An
agent that stopped instead would never take part in shutdown, and the
office would hang.
"""

from __future__ import annotations

import sys
import traceback
from abc import ABC, abstractmethod
from threading import Thread
from typing import TYPE_CHECKING, Any, Protocol

from dissyslab.runtime.messages import _OsMessage, _ShutdownSignal
from dissyslab.runtime.os_hooks import OsHooks

if TYPE_CHECKING:
    from dissyslab.builder import PortReference


class QueueLike(Protocol):
    """What an agent needs from a queue: ``put`` and a blocking ``get``."""

    def get(self) -> Any: ...

    def put(self, item: Any) -> None: ...


# ── Errors reported as data ─────────────────────────────────────────────────

ERROR_TYPE_SUFFIX = "_error"


def is_error_message(msg: Any) -> bool:
    """True when ``msg`` is a component reporting a failure as data.

    A polling source that survives one bad fetch sends
    ``{"type": "<component>_error", "error": "..."}`` instead of crashing.
    ``send`` counts these, so the run summary can say that a source sent
    only errors instead of reporting a clean, empty run. Matches the
    ``type`` field only, and only a string ending in ``_error``.
    """
    return bool(
        isinstance(msg, dict)
        and isinstance(msg.get("type"), str)
        and msg["type"].endswith(ERROR_TYPE_SUFFIX)
    )


# ── The thread an agent runs in ─────────────────────────────────────────────


class ExceptionThread(Thread):
    """A thread that keeps the exception its target raised, for the summary."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.exception: Exception | None = None
        self.exc_info: tuple[Any, ...] | None = None

    def run(self) -> None:
        try:
            super().run()
        except Exception as e:
            self.exception = e
            self.exc_info = sys.exc_info()


# ── Agent ───────────────────────────────────────────────────────────────────


class Agent(OsHooks, ABC):
    """Base class for every agent in a network.

    Subclasses define ``run``; most never override anything else.

    Lifecycle, driven by the network: ``startup()`` once, then ``run()``
    in the agent's own thread until the network shuts down, then
    ``shutdown()``.
    """

    def __init__(
        self,
        *,
        name: str | None = None,
        inports: list[str] | None = None,
        outports: list[str] | None = None,
    ) -> None:
        self.inports: list[str] = list(inports) if inports is not None else []
        self.outports: list[str] = list(outports) if outports is not None else []

        # One queue per port, connected by the network before threads start.
        self.in_q: dict[str, Any] = {p: None for p in self.inports}
        self.out_q: dict[str, Any] = {p: None for p in self.outports}

        # Given by the network if not here; a nested office's agents get
        # their full path, e.g. "root::spam_filter".
        self.name: str | None = name

        # Office messages sent and received per port. The termination
        # detector compares these; operating-system messages never count.
        self.sent: dict[str, int] = {p: 0 for p in self.outports}
        self.received: dict[str, int] = {p: 0 for p in self.inports}

        # Error reports this agent passed on as data (see is_error_message),
        # per outbox, and the first one's text for the run summary.
        self.errors: dict[str, int] = {p: 0 for p in self.outports}
        self.first_error: str | None = None

        # Messages this agent could not handle itself (see report_failure),
        # and the first one's description for the run summary.
        self.failures: int = 0
        self.first_failure: str | None = None

        # The termination detector's queue; set by the network.
        self.os_q: Any = None

        self._os_init()

    # ── Lifecycle ──────────────────────────────────────────────────────────

    def startup(self) -> None:
        """Called once before ``run``. Override for one-time setup."""

    @abstractmethod
    def run(self) -> None:
        """The agent's work: typically a loop of ``recv`` and ``send``."""
        raise NotImplementedError("Subclasses must implement run()")

    def shutdown(self) -> None:
        """Called once after ``run`` has ended. Override for cleanup."""

    def start(self) -> None:
        """Run the agent until the network shuts it down. Do not override.

        The network's thread calls this. ``recv`` raises
        ``_ShutdownSignal`` when the termination detector has declared the
        network finished; that ends ``run`` here, cleanly.
        """
        try:
            self.run()
        except _ShutdownSignal:
            pass

    # ── Sending and receiving ──────────────────────────────────────────────

    def send(self, msg: Any, outport: str) -> None:
        """Put ``msg`` on the queue of ``outport``. Never blocks.

        ``None`` is not sent. Office messages are counted; an error report
        (see ``is_error_message``) is also counted as an error.
        """
        if outport not in self.outports:
            raise ValueError(
                f"'{outport}' is not a valid outbox of agent '{self.name}'. "
                f"Valid outboxes: {self.outports}"
            )
        q = self.out_q[outport]
        if q is None:
            raise ValueError(f"Outbox '{outport}' of agent '{self.name}' is not connected.")
        if msg is None:
            return

        q.put(self._os_wrap_outgoing(msg, outport))  # OS: tracing stamp, if on

        if not isinstance(msg, _OsMessage):
            self.sent[outport] += 1
            if is_error_message(msg):
                self.errors[outport] += 1
                if self.first_error is None:
                    detail = msg.get("error")
                    self.first_error = str(detail) if detail else str(msg.get("type"))

    def recv(self, inport: str) -> Any:
        """Return the next office message on ``inport``, waiting if necessary.

        Operating-system messages that arrive on the same queue are handled
        here and never returned (see ``OsHooks._os_intercept``).
        """
        if inport not in self.inports:
            raise ValueError(
                f"'{inport}' is not a valid inbox of agent '{self.name}'. "
                f"Valid inboxes: {self.inports}"
            )
        q = self.in_q[inport]
        if q is None:
            raise ValueError(f"Inbox '{inport}' of agent '{self.name}' is not connected.")

        while True:
            # OS: after a resume, first replay what was in transit.
            replayed, msg = self._os_take_recovered(inport)
            if replayed:
                self.received[inport] += 1
                self._os_trace_received(inport, msg, None)
                return msg

            msg, incoming_ts = self._os_unwrap(q.get())  # OS: tracing stamp, if any
            if self._os_intercept(msg, inport):  # OS: an operating-system message
                continue
            if not self._os_accept(msg, inport):  # OS: snapshot recording / recovery
                continue
            self.received[inport] += 1
            self._os_trace_received(inport, msg, incoming_ts)  # OS: trace, if on
            return msg

    # ── Failures ───────────────────────────────────────────────────────────

    def report_failure(self, exc: BaseException, doing: str = "its work") -> None:
        """This agent could not handle one message: count it, say so once.

        Call it from an ``except`` block and carry on with the next
        message. Only the first failure is printed (to stderr, as one
        write, so it is not spliced into other agents' output); the rest
        are counted and the run summary prints the count.
        """
        first = self.first_failure is None
        self.record_failure(f"{type(exc).__name__}: {exc}")
        if not first:
            return
        sys.stderr.write(
            f"\n[{type(self).__name__} '{self.name}'] "
            f"{type(exc).__name__}: {exc}\n"
            f"{traceback.format_exc()}"
            f"This message was not processed while {self.name} was doing "
            f"{doing}. The office carries on; the run summary counts the "
            f"rest.\n\n"
        )
        sys.stderr.flush()

    def record_failure(self, detail: str) -> None:
        """Count one failure without printing; keep the first description."""
        self.failures += 1
        if self.first_failure is None:
            self.first_failure = str(detail)

    # ── State, for snapshots ───────────────────────────────────────────────

    def save_state(self) -> Any:
        """Return the state that must survive a snapshot (default: none).

        A stateful agent returns a small object that ``pickle`` can save,
        holding only what cannot be rebuilt: counters, cursors, seen-sets.
        Models, open files and other resources are rebuilt, not saved.
        """
        return {}

    def load_state(self, state: Any) -> None:
        """Restore what ``save_state`` returned (default: nothing to do).

        Called during recovery, before ``recv`` returns the first message
        after the resume.
        """

    # ── Default ports, for connections that name no port ──────────────────

    @property
    def default_inport(self) -> str | None:
        """``in_`` if the agent has it, else None."""
        return "in_" if "in_" in self.inports else None

    @property
    def default_outport(self) -> str | None:
        """``out_`` if the agent has it, else None."""
        return "out_" if "out_" in self.outports else None

    # ── Python building API (to be removed with dissyslab.builder) ─────────

    def __getattr__(self, name: str) -> PortReference:
        """``agent.port_name`` gives a port reference for ``dissyslab.builder``."""
        from dissyslab.builder import PortReference

        if name in self.inports or name in self.outports:
            return PortReference(agent=self, port_name=name)
        raise AttributeError(
            f"'{type(self).__name__}' object has no attribute '{name}'. "
            f"Valid mailboxes: inboxes={self.inports}, outboxes={self.outports}"
        )
