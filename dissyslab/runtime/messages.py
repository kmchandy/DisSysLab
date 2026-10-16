"""Messages the operating system sends, and the signal that ends an agent.

These travel through the same queues as an office's own messages, but a
role never sees them: ``Agent.recv`` intercepts every one of them (see
:mod:`dissyslab.runtime.os_hooks`). They are never counted in an agent's
``sent`` and ``received`` totals.

Moved unchanged from ``dissyslab/core.py`` (restructure_plan.md, Phase 1).
The algorithms that use them are described in
``docs/algorithms/CHECKPOINT_RESUME.md`` (snapshots and recovery),
``docs/internals/design/termination_detection_design.md`` (termination)
and ``docs/algorithms/TRACE_AND_LOGICAL_CLOCK.md`` (tracing).
"""

from __future__ import annotations

from typing import Any


class _OsMessage:
    """Base class for all operating-system messages. Never counted."""


class _TimerFired(_OsMessage):
    """An Alarm's worker thread reporting that its wait has expired.

    Put directly on the alarm's own inbox queue (not via ``send``, which is
    for outboxes). Being an ``_OsMessage`` keeps it out of the alarm's
    ``received`` count, so the alarm's idleness test stays honest. The
    worker never calls ``send`` itself: a snapshot needs each agent to
    record its state atomically with respect to its own sends and
    receives, and a second sending thread would break that.
    """


class _GiveMeCounts(_OsMessage):
    """The termination detector asking an agent for its message counts.

    ``round_id`` tags the polling round. The agent echoes it back, which
    tells the detector that the agent is blocked in ``recv`` right now.
    """

    def __init__(self, round_id: int | None = None) -> None:
        self.round_id = round_id


class _Shutdown(_OsMessage):
    """The termination detector telling an agent to stop."""


class _ShutdownSignal(Exception):
    """Raised inside ``recv`` when ``_Shutdown`` arrives; ends ``run``."""


# ── Snapshot and recovery (Chandy-Lamport) ─────────────────────────────────


class _Checkpoint(_OsMessage):
    """The marker for snapshot N.

    Starts at the sources and travels downstream: an agent that receives
    ``_Checkpoint(N)`` on an inbox for the first time forwards it on every
    outbox. Duplicates are ignored by the receiver.
    """

    def __init__(self, N: int) -> None:
        self.N = N


class _Reply(_OsMessage):
    """Agent to operating system: "snapshot N is complete for me."

    Carries the agent's saved state and, for each inbox, the messages
    recorded on it between the agent's first marker and the marker on
    that inbox (the channel state).
    """

    def __init__(
        self, N: int, agent: str, state: Any, channel_states: dict[str, list[Any]]
    ) -> None:
        self.N = N
        self.agent = agent
        self.state = state
        self.channel_states = channel_states


class _PrepareRecover(_OsMessage):
    """Operating system to agents: stop, load snapshot N, and wait."""

    def __init__(self, N: int) -> None:
        self.N = N


class _RecoverReady(_OsMessage):
    """Agent to operating system: "I have loaded snapshot N and am waiting." """

    def __init__(self, N: int, agent: str) -> None:
        self.N = N
        self.agent = agent


class _StartRecover(_OsMessage):
    """Operating system to agents: recovery barrier released; carry on."""

    def __init__(self, N: int) -> None:
        self.N = N


# ── Tracing ─────────────────────────────────────────────────────────────────


class _Timestamped:
    """An office message wrapped with its sender's logical-clock value.

    Not an ``_OsMessage``: it carries an office's own message. ``send``
    wraps and ``recv`` unwraps, and only when tracing is on, so a role
    never sees the wrapper.
    """

    __slots__ = ("payload", "clock")

    def __init__(self, payload: Any, clock: int) -> None:
        self.payload = payload
        self.clock = clock
