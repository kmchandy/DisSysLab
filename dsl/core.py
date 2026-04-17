# dsl/core.py
"""
Core building blocks for the DSL distributed systems framework.

This module provides:
- OS message classes for termination detection
- Agent: Abstract base class for all network nodes
- ExceptionThread: Thread that captures exceptions for debugging
"""

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

# Connection tuple: (from_block, from_port, to_block, to_port)
Connection = Tuple[str, str, str, str]

# Type alias for blocks (Agent or Network)
Block = Union["Agent", "Network"]


# ============================================================================
# Protocol for Queue-like Objects
# ============================================================================

class QueueLike(Protocol):
    """Protocol for queue-like objects that support get() and put()."""

    def get(self) -> Any: ...
    def put(self, item: Any) -> None: ...


# ============================================================================
# OS Message Classes
# ============================================================================

class _OsMessage:
    """Base class for all OS messages. Never counted in sent/received."""
    pass


class _GiveMeCounts(_OsMessage):
    """Sent by os_agent to request current sent/received counts from a client."""
    pass


class _Shutdown(_OsMessage):
    """Sent by os_agent to tell a client agent to terminate."""
    pass


class _ShutdownSignal(Exception):
    """Raised inside recv() when _Shutdown is received. Unwinds run() cleanly."""
    pass


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
    Must be module-level so multiprocessing can pickle it.
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
    """

    def __init__(self, target, name=None, daemon=False):
        self._exc_queue = multiprocessing.Queue()
        super().__init__(
            target=_process_worker,
            args=(target, self._exc_queue),
            name=name,
            daemon=daemon
        )
        self.exception = None
        self.traceback_str = None

    def join(self, timeout=None):
        """Join process and retrieve any exception from the child."""
        super().join(timeout=timeout)
        if not self._exc_queue.empty():
            self.exception, self.traceback_str = self._exc_queue.get_nowait()


# ============================================================================
# Agent Base Class
# ============================================================================

class Agent(ABC):
    """
    Base class for all nodes in a flow-based programming network.

    An Agent is a processing unit that:
    - Receives messages on input ports (inports)
    - Processes messages in its run() method
    - Sends messages on output ports (outports)
    - Runs in its own thread when the network executes

    **Lifecycle:**
    1. __init__(): Define ports, initialize state
    2. startup(): One-time initialization before run() (optional override)
    3. run(): Main processing loop (MUST override - abstract method)
    4. shutdown(): Cleanup after run() completes (optional override)

    **Termination:**
    Termination is detected by os_agent, which polls agents periodically
    via _GiveMeCounts messages and declares termination by sending _Shutdown.
    Agents do not need to handle termination explicitly — recv() handles
    OS messages transparently.

    **Message Passing:**
    - recv(inport): Blocking read, intercepts OS messages transparently
    - send(msg, outport): Non-blocking write, counts client messages
    - send_os(msg): Sends directly to os_agent's queue (framework use only)
    - None messages are automatically filtered (not sent downstream)
    """

    def __init__(
        self,
        *,
        name: Optional[str] = None,
        inports: Optional[List[str]] = None,
        outports: Optional[List[str]] = None,
    ):
        # Avoid mutable-default traps
        self.inports: List[str] = list(inports) if inports is not None else []
        self.outports: List[str] = list(
            outports) if outports is not None else []

        # Queue dictionaries - wired during Network.compile()
        self.in_q: Dict[str, Optional[QueueLike]] = {
            p: None for p in self.inports}
        self.out_q: Dict[str, Optional[QueueLike]] = {
            p: None for p in self.outports}

        # Name — optional at construction, assigned by Network during compilation
        # After flattening, updated to full path (e.g. "root::spam_filter")
        self.name: Optional[str] = name

        # Message counters — maintained by send() and recv()
        # OS messages (_OsMessage) are never counted
        self.sent:     Dict[str, int] = {p: 0 for p in self.outports}
        self.received: Dict[str, int] = {p: 0 for p in self.inports}

        # Queue to os_agent — injected by network.py during _create_os_agent()
        # Always set before threads start, never None at runtime
        self.os_q: Optional[QueueLike] = None

    # ========== Lifecycle Methods ==========

    def startup(self) -> None:
        """One-time initialization before run() is called."""
        pass

    @abstractmethod
    def run(self) -> None:
        """Main processing loop - MUST be implemented by subclasses."""
        raise NotImplementedError("Subclasses must implement run()")

    def shutdown(self) -> None:
        """Cleanup after run() completes."""
        pass

    def start(self) -> None:
        """
        Framework entry point — called by threads in network.py.
        Calls run() and catches _ShutdownSignal for clean exit.
        Do not override this method.
        """
        try:
            self.run()
        except _ShutdownSignal:
            pass  # clean exit — os_agent declared termination

    # ========== Message Passing ==========

    def send(self, msg: Any, outport: str) -> None:
        """
        Send a message to an output port.
        Counts client messages. OS messages and None are not counted.
        """
        if outport not in self.outports:
            raise ValueError(
                f"Port '{outport}' is not a valid outport of agent '{self.name}'. "
                f"Valid outports: {self.outports}"
            )

        q = self.out_q[outport]
        if q is None:
            raise ValueError(
                f"Outport '{outport}' of agent '{self.name}' is not connected."
            )

        if msg is None:
            return

        q.put(msg)

        # Count only client messages
        if not isinstance(msg, _OsMessage):
            self.sent[outport] += 1

    def recv(self, inport: str) -> Any:
        """
        Receive a message from an input port (blocking).

        Transparently intercepts OS messages:
        - _GiveMeCounts: responds with current counts via send_os()
        - _Shutdown: raises _ShutdownSignal to unwind run()

        Client messages are counted and returned to the caller.
        """
        if inport not in self.inports:
            raise ValueError(
                f"Port '{inport}' is not a valid inport of agent '{self.name}'. "
                f"Valid inports: {self.inports}"
            )

        q = self.in_q[inport]
        if q is None:
            raise ValueError(
                f"Inport '{inport}' of agent '{self.name}' is not connected."
            )

        while True:
            msg = q.get()

            if isinstance(msg, _GiveMeCounts):
                # Respond with current counts — framework handles this
                self.send_os({
                    "agent":    self.name,
                    "sent":     dict(self.sent),
                    "received": dict(self.received),
                })

            elif isinstance(msg, _Shutdown):
                # Unwind run() cleanly
                raise _ShutdownSignal()

            else:
                # Client message — count and return
                self.received[inport] += 1
                return msg

    def send_os(self, msg: Any) -> None:
        """
        Send a message directly to os_agent's input queue.
        Used by recv() to respond to _GiveMeCounts.
        Framework use only — not for client code.
        """
        if self.os_q is not None:
            self.os_q.put(msg)

    # ========== Default Port Properties ==========

    @property
    def default_inport(self) -> Optional[str]:
        """Default input port for edge syntax without explicit port."""
        return "in_" if "in_" in self.inports else None

    @property
    def default_outport(self) -> Optional[str]:
        """Default output port for edge syntax without explicit port."""
        return "out_" if "out_" in self.outports else None

    # ========== Port Reference Support ==========

    def __getattr__(self, name: str) -> 'PortReference':
        """Enable dot notation for ports: agent.port_name"""
        from dissyslab.builder import PortReference

        if name in self.inports or name in self.outports:
            return PortReference(agent=self, port_name=name)

        raise AttributeError(
            f"'{type(self).__name__}' object has no attribute '{name}'. "
            f"Valid ports: inports={self.inports}, outports={self.outports}"
        )
