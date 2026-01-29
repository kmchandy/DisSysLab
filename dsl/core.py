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

    **Name Assignment:**
    The `name` parameter is REQUIRED and must be provided in __init__.
    """

    def __init__(
        self,
        *,
        name: str,
        inports: Optional[List[str]] = None,
        outports: Optional[List[str]] = None
    ):
        """Initialize an Agent with required name and optional ports."""
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
        self.in_q: Dict[str, Optional[QueueLike]] = {
            p: None for p in self.inports}
        self.out_q: Dict[str, Optional[QueueLike]] = {
            p: None for p in self.outports}

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

    # ========== Message Passing ==========

    def send(self, msg: Any, outport: str) -> None:
        """Send a message to an output port."""
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

        # Filter out None messages
        if msg is None:
            return

        q.put(msg)

    def recv(self, inport: str) -> Any:
        """Receive a message from an input port (blocking)."""
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

        return q.get()

    def broadcast_stop(self) -> None:
        """Send STOP signal to all downstream agents via all outports."""
        for outport in self.outports:
            self.send(STOP, outport)

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
        from dsl.builder import PortReference

        if name in self.inports or name in self.outports:
            return PortReference(agent=self, port_name=name)

        raise AttributeError(
            f"'{type(self).__name__}' object has no attribute '{name}'. "
            f"Valid ports: inports={self.inports}, outports={self.outports}"
        )
