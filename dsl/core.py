# dsl/core.py
"""
Core building blocks for the DSL distributed systems framework.

This module provides:
- STOP: Sentinel for end-of-stream signaling
- Agent: Abstract base class for all network nodes
- ExceptionThread: Thread that captures exceptions for debugging
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from threading import Thread
from typing import Any, Dict, List, Optional, Protocol
import sys


# ============================================================================
# Type Definitions
# ============================================================================

class QueueLike(Protocol):
    """Protocol for queue-like objects that support get() and put()."""

    def get(self) -> Any: ...
    def put(self, item: Any) -> None: ...


# ============================================================================
# STOP Sentinel
# ============================================================================

class _Stop:
    """Sentinel object for end-of-stream signaling."""

    def __repr__(self) -> str:
        return "STOP"


STOP = _Stop()


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
# Agent Base Class
# ============================================================================

class Agent(ABC):
    """
    Base class for all agents in the network.

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

    **Ports:**
    - Inports: Named inputs that receive messages
    - Outports: Named outputs that send messages
    - Port names must be unique within the agent
    - Network automatically handles fanout (one → many) and fanin (many → one)

    **Port References:**
    - Access ports via dot notation: agent.port_name returns PortReference
    - Used in network edges: (source.out_, transform.in_)

    **Message Passing:**
    - recv(inport): Blocking read from an input port
    - send(msg, outport): Non-blocking write to an output port
    - Messages can be any pickleable Python object
    - None messages are automatically filtered (not sent downstream)
    - STOP signals indicate end-of-stream

    **STOP Signal Handling:**
    - When receiving STOP: call broadcast_stop() and return from run()
    - This ensures downstream agents are notified to terminate

    **Name Assignment:**
    The `name` parameter is REQUIRED and must be provided in __init__.
    Used for debugging, error messages, and network visualization.
    """

    def __init__(
        self,
        *,
        name: str,
        inports: Optional[List[str]] = None,
        outports: Optional[List[str]] = None
    ):
        """
        Initialize an Agent with required name and optional ports.

        Args:
            name: Unique name for this agent (REQUIRED, non-empty string)
            inports: List of input port names (default: empty list)
            outports: List of output port names (default: empty list)

        Raises:
            ValueError: If name is empty or None
            TypeError: If name is not a string
            TypeError: If port names are not strings
            ValueError: If port names are duplicated within the agent

        Note:
            Queues (in_q, out_q) are wired during Network.compile().
        """
        # Validate name (REQUIRED parameter)
        if not name:
            raise ValueError("Agent name is required and cannot be empty")
        if not isinstance(name, str):
            raise TypeError(
                f"Agent name must be string, got {type(name).__name__}")

        self.name = name

        # Avoid mutable default trap
        self.inports: List[str] = list(inports) if inports is not None else []
        self.outports: List[str] = list(
            outports) if outports is not None else []

        # Validate all port names are strings
        for port in self.inports + self.outports:
            if not isinstance(port, str):
                raise TypeError(
                    f"Port names must be strings, got {type(port).__name__}: {port!r}"
                )

        # Check uniqueness across all ports
        all_ports = self.inports + self.outports
        if len(set(all_ports)) != len(all_ports):
            # Find duplicates
            seen = set()
            duplicates = set()
            for port in all_ports:
                if port in seen:
                    duplicates.add(port)
                seen.add(port)

            raise ValueError(
                f"Port names must be unique within agent '{name}'. "
                f"Duplicate port name(s): {sorted(duplicates)}"
            )

        # Queue dictionaries - wired by Network during compilation
        # Values are None until connected, then become QueueLike objects
        self.in_q: Dict[str, Optional[QueueLike]] = {
            p: None for p in self.inports}
        self.out_q: Dict[str, Optional[QueueLike]] = {
            p: None for p in self.outports}

    # ========== Lifecycle Methods ==========

    def startup(self) -> None:
        """
        One-time initialization before run() is called.

        Override this to:
        - Open files or network connections
        - Initialize resources
        - Perform setup that requires the network to be compiled

        Called once per agent before any threads start.
        Exceptions here will prevent the network from starting.
        """
        pass

    @abstractmethod
    def run(self) -> None:
        """
        Main processing loop - MUST be implemented by subclasses.

        This is where the agent does its work:
        - Receive messages from input ports
        - Process data
        - Send results to output ports
        - Handle STOP signals

        Runs in its own thread. Should loop until:
        - STOP signal received, or
        - Processing complete (for sources)

        Typical pattern:
            while True:
                msg = self.recv("in_")
                if msg is STOP:
                    self.broadcast_stop()
                    return
                # ... process msg ...
                self.send(result, "out_")
        """
        raise NotImplementedError("Subclasses must implement run()")

    def shutdown(self) -> None:
        """
        Cleanup after run() completes.

        Override this to:
        - Close files or network connections
        - Release resources
        - Save final state

        Called once per agent after all threads have joined.
        Exceptions here are logged but don't prevent other agents from shutting down.
        """
        pass

    # ========== Message Passing ==========

    def send(self, msg: Any, outport: str) -> None:
        """
        Send a message to an output port.

        Args:
            msg: Message to send (any pickleable Python object, or STOP)
            outport: Name of the output port

        Behavior:
            - None messages are filtered (not sent downstream)
            - STOP and all other messages pass through
            - Non-blocking operation (queue.put)

        Raises:
            ValueError: If outport doesn't exist or isn't connected
        """
        # Validate outport exists
        if outport not in self.outports:
            raise ValueError(
                f"Port '{outport}' is not a valid outport of agent '{self.name}'. "
                f"Valid outports: {self.outports}"
            )

        # Get queue
        q = self.out_q[outport]
        if q is None:
            raise ValueError(
                f"Outport '{outport}' of agent '{self.name}' is not connected to any queue. "
                f"This should not happen if network was validated."
            )

        # Filter out None messages - they are dropped, not sent downstream
        # STOP and all other messages pass through
        if msg is None:
            return

        # Send message
        q.put(msg)

    def recv(self, inport: str) -> Any:
        """
        Receive a message from an input port (blocking).

        Args:
            inport: Name of the input port

        Returns:
            The received message (any Python object or STOP)

        Behavior:
            - Blocks until a message is available
            - Returns the message (could be data or STOP signal)

        Raises:
            ValueError: If inport doesn't exist or isn't connected
        """
        # Validate inport exists
        if inport not in self.inports:
            raise ValueError(
                f"Port '{inport}' is not a valid inport of agent '{self.name}'. "
                f"Valid inports: {self.inports}"
            )

        # Get queue
        q = self.in_q[inport]
        if q is None:
            raise ValueError(
                f"Inport '{inport}' of agent '{self.name}' is not connected to any queue. "
                f"This should not happen if network was validated."
            )

        # Receive message (blocking)
        return q.get()

    def broadcast_stop(self) -> None:
        """
        Send STOP signal to all downstream agents via all outports.

        Call this when:
        - Receiving STOP from upstream
        - Completing processing (for sources)
        - Encountering an unrecoverable error

        This ensures downstream agents are notified to terminate gracefully.
        """
        for outport in self.outports:
            self.send(STOP, outport)

    # ========== Default Port Properties ==========

    @property
    def default_inport(self) -> Optional[str]:
        """
        Default input port for edge syntax without explicit port.

        Override in subclasses to enable: (source, self)

        Base implementation returns "in_" if it exists, None otherwise.

        Returns:
            Port name or None if no default/ambiguous
        """
        return "in_" if "in_" in self.inports else None

    @property
    def default_outport(self) -> Optional[str]:
        """
        Default output port for edge syntax without explicit port.

        Override in subclasses to enable: (self, sink)

        Base implementation returns "out_" if it exists, None otherwise.

        Returns:
            Port name or None if no default/ambiguous
        """
        return "out_" if "out_" in self.outports else None

    # ========== Port Reference Support ==========

    def __getattr__(self, name: str) -> 'PortReference':
        """
        Enable dot notation for ports: agent.port_name

        Creates PortReference objects for use in network() edges.

        Example:
            >>> source.out_  # Returns PortReference(source, "out_")
            >>> sink.in_     # Returns PortReference(sink, "in_")

        Args:
            name: Attribute name being accessed

        Returns:
            PortReference if name is a valid port

        Raises:
            AttributeError: If name is not a valid port
        """
        # Import here to avoid circular dependency
        # (Agent needs PortReference, PortReference needs Agent)
        from dsl.builder import PortReference

        # Check if it's a valid port (search both inports and outports)
        if name in self.inports or name in self.outports:
            return PortReference(agent=self, port_name=name)

        # Not a port - raise standard AttributeError
        raise AttributeError(
            f"'{type(self).__name__}' object has no attribute '{name}'. "
            f"Valid ports: inports={self.inports}, outports={self.outports}"
        )
