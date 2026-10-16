"""Moved to :mod:`dissyslab.runtime` (restructure_plan.md, Phase 1).

- ``Agent``, ``ExceptionThread``, ``QueueLike``, ``is_error_message``:
  :mod:`dissyslab.runtime.agent`
- the operating system's messages and ``_ShutdownSignal``:
  :mod:`dissyslab.runtime.messages`
- the operating system's per-agent state and handlers:
  :mod:`dissyslab.runtime.os_hooks`

Kept so existing imports keep working until Phase 5 removes it.
"""

from dissyslab.runtime.agent import (
    ERROR_TYPE_SUFFIX,
    Agent,
    ExceptionThread,
    QueueLike,
    is_error_message,
)
from dissyslab.runtime.messages import (
    _Checkpoint,
    _GiveMeCounts,
    _OsMessage,
    _PrepareRecover,
    _RecoverReady,
    _Reply,
    _Shutdown,
    _ShutdownSignal,
    _StartRecover,
    _TimerFired,
    _Timestamped,
)
from dissyslab.runtime.os_hooks import _NO_LOCK, _NoLock, _SnapshotState

__all__ = [
    "ERROR_TYPE_SUFFIX",
    "Agent",
    "ExceptionThread",
    "QueueLike",
    "is_error_message",
    "_Checkpoint",
    "_GiveMeCounts",
    "_OsMessage",
    "_PrepareRecover",
    "_RecoverReady",
    "_Reply",
    "_Shutdown",
    "_ShutdownSignal",
    "_StartRecover",
    "_TimerFired",
    "_Timestamped",
    "_NO_LOCK",
    "_NoLock",
    "_SnapshotState",
]
