# dsl/core.py
from __future__ import annotations
from queue import SimpleQueue
from threading import Thread
from typing import Optional, List, Dict, Tuple, Union, Any, Protocol
from collections import deque
from abc import ABC, abstractmethod
import sys
import multiprocessing


# ============================================================================
# Type Definitions
# ============================================================================

# Sentinel object for end-of-stream signaling
class _Stop:
    """Sentinel object for end-of-stream signaling."""

    def __repr__(self):
        return "STOP"


STOP = _Stop()

# Connection tuple: (from_block, from_port, to_block, to_port)
Connection = Tuple[str, str, str, str]

# Type alias for blocks (Agent or Network)
Block = Union["Agent", "Network"]


# ============================================================================
# Protocol for Queue-like Objects
# ============================================================================

class QueueLike(Protocol):
    """Protocol for queue-like objects that support get() and put().

    This allows flexibility in queue implementation - could be SimpleQueue,
    multiprocessing.Queue, or any other queue-like object.
    """

    def get(self) -> Any: ...
    def put(self, item: Any) -> None: ...


# ============================================================================
# Exception-Capturing Thread
# ============================================================================

class ExceptionThread(Thread):
    """Thread that captures exceptions from target function for debugging."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.exception: Optional[Exception] = None
        self.exc_info: Optional[tuple] = None

    def run(self):
        try:
            super().run()
        except Exception as e:
            self.exception = e
            self.exc_info = sys.exc_info()


# ============================================================================
# Exception-Capturing Process
# ============================================================================

def _process_worker(target, exc_queue):
    """
    Top-level worker function for ExceptionProcess.

    Must be a module-level function (not a lambda or nested function)
    so that multiprocessing can pickle it on all platforms.

    Runs target(), catches any exception, and puts it on exc_queue
    so the parent process can retrieve and re-raise it.
    """
    try:
        target()
    except Exception as e:
        import traceback
        exc_queue.put((e, traceback.format_exc()))


class ExceptionProcess(multiprocessing.Process):
    """
    Process that captures exceptions from target function for debugging.

    Mirrors ExceptionThread but for multiprocessing.Process.

    Key difference from ExceptionThread: child process exceptions do not
    propagate to the parent automatically. We use a multiprocessing.Queue
    to ship the exception and traceback string back to the parent, where
    process_network() can retrieve and report them.

    Usage is identical to ExceptionThread from the caller's perspective:
        p = ExceptionProcess(target=agent.run, name="agent_process")
        p.start()
        p.join()
        if p.exception:
            print(p.traceback_str)
    """

    def __init__(self, target, name=None, daemon=False):
        # exc_queue carries (exception, traceback_string) back to parent
        self._exc_queue = multiprocessing.Queue()
        super().__init__(
            target=_process_worker,
            args=(target, self._exc_queue),
            name=name,
            daemon=daemon
        )
        self.exception: Optional[Exception] = None
        self.traceback_str: Optional[str] = None

    def join(self, timeout=None):
        """Join process and retrieve any exception from the child."""
        super().join(timeout=timeout)
        # Drain the exception queue after join
        if not self._exc_queue.empty():
            self.exception, self.traceback_str = self._exc_queue.get_nowait()
