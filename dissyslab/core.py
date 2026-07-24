# dissyslab/core.py
"""
Core building blocks for the DSL distributed systems framework.

This module provides:
- OS message classes for termination detection
- Agent: Abstract base class for all network nodes
- ExceptionThread: Thread that captures exceptions for debugging
"""

from __future__ import annotations
from queue import SimpleQueue, Empty
from threading import Thread, Lock
from typing import Optional, List, Dict, Tuple, Union, Any, Protocol
from collections import deque
from abc import ABC, abstractmethod
from enum import Enum
from pathlib import Path
import sys
import time
import json
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
    """Sent by os_agent to request current sent/received counts from a client.

    ``round_id`` tags the polling round this request belongs to. An agent
    echoes it back in its reply, which lets os_agent tell that every
    non-source agent is *currently* blocked in recv (i.e. passive) — a
    precondition for declaring termination. ``None`` for legacy callers.
    """

    def __init__(self, round_id: Optional[int] = None):
        self.round_id = round_id


class _Shutdown(_OsMessage):
    """Sent by os_agent to tell a client agent to terminate."""
    pass


class _ShutdownSignal(Exception):
    """Raised inside recv() when _Shutdown is received. Unwinds run() cleanly."""
    pass


# ── Checkpoint-Resume OS messages (added v1.6) ────────────────────────────
# These implement the Chandy-Lamport distributed snapshot algorithm.
# See docs/algorithms/CHECKPOINT_RESUME.md for the full specification.

class _Checkpoint(_OsMessage):
    """Marker for snapshot N.

    Put in each source's input queue by the OS manager to initiate
    snapshot N. Propagates downstream because every agent that
    receives _Checkpoint(N) on a data inport for the first time
    forwards _Checkpoint(N) on every one of its outports.

    Multi-worker agents (MergeAsynch) may forward more than once
    on the same outport; receivers deduplicate by the subsequent-
    marker rule (idempotent on duplicate arrivals per inport).
    """

    def __init__(self, N: int):
        self.N = N


class _Reply(_OsMessage):
    """Agent → OS: "snapshot N for me is complete."

    Carries the agent's saved state (the value returned by
    save_state) and the per-inport channel-state recording (a
    dict mapping inport name to a list of data messages received
    on that inport between when this agent first saw _Checkpoint(N)
    and when _Checkpoint(N) arrived on the inport).

    Travels on the existing os_q back-channel that today carries
    _GiveMeCounts replies.
    """

    def __init__(self, N: int, agent: str, state: Any, channel_states: dict):
        self.N = N
        self.agent = agent
        self.state = state
        self.channel_states = channel_states


class _PrepareRecover(_OsMessage):
    """OS broadcast: stop, load checkpoint N, fill recovery buffer, wait.

    Put in each source's input queue by the OS manager at the start
    of recovery from snapshot N. Propagates downstream like
    _Checkpoint. Each agent on receipt loads its checkpoint-N state
    from disk via load_state(), fills a per-inport recovery buffer
    from the on-disk channel-state files, sends _RecoverReady on
    os_q, and enters RECOVER_WAITING.
    """

    def __init__(self, N: int):
        self.N = N


class _RecoverReady(_OsMessage):
    """Agent → OS: "I have stopped, loaded state, and am waiting."

    Travels on the existing os_q back-channel.
    """

    def __init__(self, N: int, agent: str):
        self.N = N
        self.agent = agent


class _StartRecover(_OsMessage):
    """OS broadcast: release the recovery barrier; resume execution.

    Put in each source's input queue by the OS manager only after
    every agent's _RecoverReady has been received. Propagates
    downstream like _Checkpoint. Each agent on receipt exits
    RECOVER_WAITING; subsequent recv() calls serve from the
    per-inport recovery buffer first, then from the inport queue.
    """

    def __init__(self, N: int):
        self.N = N


# ── Trace-mode message wrapper (added v1.7) ───────────────────────────────
# See docs/algorithms/TRACE_AND_LOGICAL_CLOCK.md. Data-plane, not control
# plane — unlike the _OsMessage subclasses above, this wraps a *client*
# message so its logical-clock timestamp can travel with it on the wire.
# send() wraps a client message in _Timestamped(msg, clock) right before
# q.put(); recv() unwraps it immediately after q.get() (or after the
# recovery-buffer pop), before any of the existing OS-message dispatch or
# checkpoint channel-state recording sees it. Only present when tracing
# is enabled (self._trace_dir is not None) — a normal run never
# constructs or sees one of these, so behaviour is unchanged when tracing
# is off.

class _Timestamped:
    """Wraps a client message with its sender's logical-clock value.

    Not an _OsMessage — this travels through the same queues as ordinary
    client data, invisible to client code (send()/recv() add and remove
    the wrapper transparently).
    """
    __slots__ = ("payload", "clock")

    def __init__(self, payload: Any, clock: int):
        self.payload = payload
        self.clock = clock


# ── No-op lock for single-threaded agents (added v1.6) ────────────────────
# Concurrency on snapshot state exists only in MergeAsynch, which has one
# worker thread per inport. Every other agent has a single execution
# thread and needs no synchronization on its own state. To keep the
# snapshot handler code uniform — `with self._snapshot_lock: ...` —
# every Agent gets a lock attribute initialised to this no-op singleton;
# MergeAsynch.__init__ replaces it with a real threading.Lock.

class _NoLock:
    """Context-manager that does nothing. Singleton instance _NO_LOCK
    is shared by every single-threaded agent."""
    def __enter__(self): return self
    def __exit__(self, *_): return False


_NO_LOCK = _NoLock()


# ── Per-agent snapshot state machine (added v1.6) ─────────────────────────
# See docs/algorithms/CHECKPOINT_RESUME.md for the full state diagram.

class _SnapshotState(Enum):
    """The agent's current state with respect to the checkpoint-resume
    protocol.

    NORMAL — no snapshot or recovery in flight; the agent processes
        client messages as usual.
    RECORDING — a snapshot is in progress; the client layer continues
        running normally, and the OS layer is appending data messages
        to per-inport channel-state lists.
    RECOVER_WAITING — a _PrepareRecover has been received and a
        _RecoverReady has been sent; the agent has loaded its
        checkpoint-N state and is blocked awaiting _StartRecover.

    Transitions:
        NORMAL          --_Checkpoint(N)----->  RECORDING
        RECORDING       --all inports closed->  NORMAL  (and send _Reply(N))
        NORMAL          --_PrepareRecover(N)->  RECOVER_WAITING
        RECORDING       --_PrepareRecover(N)->  RECOVER_WAITING (abandons in-flight snapshot)
        RECOVER_WAITING --_StartRecover(N)--->  NORMAL
    """
    NORMAL          = "normal"
    RECORDING       = "recording"
    RECOVER_WAITING = "recover_waiting"


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

        # ── Checkpoint-resume bookkeeping (v1.6) ──────────────────────────
        # See docs/algorithms/CHECKPOINT_RESUME.md for the full state machine.
        # All access to mutable snapshot state is wrapped in
        # `with self._snapshot_lock:`. For single-threaded agents the lock
        # is the no-op singleton _NO_LOCK (acquire/release compile to
        # nothing); MergeAsynch.__init__ replaces it with a real
        # threading.Lock because its workers race on shared snapshot state.
        self._snapshot_lock: Any = _NO_LOCK

        # The agent's current state in the checkpoint-resume protocol.
        self._snapshot_state: _SnapshotState = _SnapshotState.NORMAL

        # Snapshot-in-progress data. Populated when entering RECORDING;
        # cleared when transitioning out of RECORDING. Shape:
        #   {"saved":        Any,            # the value save_state() returned
        #    "open_inports": set[str],       # inports awaiting their per-inport marker
        #    "channels":     dict[str, list] # per-inport channel-state recording
        #   }
        self._recording: Optional[dict] = None
        self._recording_N: Optional[int] = None

        # Recovery-in-progress data. Populated when entering
        # RECOVER_WAITING; consumed by recv() during the catchup phase
        # after the transition back to NORMAL.
        self._recovery_N: Optional[int] = None
        # Per-inport messages restored from the snapshot's channel-state
        # files. recv() serves these to the client before pulling from
        # the inport queue. Shape: dict[inport_name, list[Any]].
        self._recovery_buffer: Dict[str, list] = {}

        # Where snapshot files are written and read. Set by network.py
        # at compile time when the office's checkpoint directory is
        # known. None means this run is not checkpoint-enabled.
        self._snapshot_dir: Optional[Path] = None

        # ── Trace / logical-clock bookkeeping (v1.7) ──────────────────────
        # See docs/algorithms/TRACE_AND_LOGICAL_CLOCK.md. Set by
        # network.py at compile time, mirroring _snapshot_dir above.
        # None (the default) means tracing is off for this run — send()/
        # recv() then take the same code path as before v1.7, with zero
        # added overhead.
        self._trace_dir: Optional[Path] = None

        # The agent's own hybrid logical clock (Part 1 of the design
        # doc): a physical-time-grounded counter, updated by the single
        # rule `x := max(ref, x + 1)` on every send or receive, where
        # `ref` is the incoming message's timestamp (receive) or the
        # current physical time in nanoseconds (send, and the recovery-
        # replay path — see recv()). Unused when tracing is off.
        self._clock: int = 0

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

    # ========== Trace / logical clock (v1.7) ==========
    # See docs/algorithms/TRACE_AND_LOGICAL_CLOCK.md Part 1 and Part 2.
    # Both helpers are no-ops in cost/effect when self._trace_dir is
    # None (tracing off) — _tick() still runs but is cheap, and
    # _trace_write() returns immediately without touching disk.

    def _tick(self, ref: int) -> int:
        """Advance this agent's hybrid logical clock: x := max(ref, x+1).

        ``ref`` is the incoming message's timestamp for a receive, or the
        current physical time (nanoseconds since epoch) for a send —
        see the design doc's "one rule" section. Guarded by
        ``self._snapshot_lock`` because MergeAsynch runs one worker
        thread per inport and this state is shared across them (the
        same lock already used for its other shared state).
        """
        with self._snapshot_lock:
            self._clock = max(ref, self._clock + 1)
            return self._clock

    def _trace_write(self, direction: str, port: str, msg: Any, ts: int) -> None:
        """Append one JSONL line to this agent's trace file, if tracing
        is enabled. Truncates the message summary at a fixed cutoff
        (300 chars) per the design doc's decided truncation policy.
        """
        if self._trace_dir is None:
            return

        summary = repr(msg)
        _CUTOFF = 300
        if len(summary) > _CUTOFF:
            extra = len(summary) - _CUTOFF
            summary = summary[:_CUTOFF] + f"... (truncated, {extra} more chars)"

        entry = {"t": ts, "dir": direction, "port": port, "msg": summary}

        # Reuse snapshot.py's filename sanitizer: flattened agent names
        # contain "::" (DSL's nested-network path separator), which is
        # invalid in Windows filenames. Same convention as checkpoint
        # files, for the same reason.
        from dissyslab.snapshot import safe_filename

        with self._snapshot_lock:
            self._trace_dir.mkdir(parents=True, exist_ok=True)
            path = self._trace_dir / f"{safe_filename(self.name)}.jsonl"
            with open(path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")

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

        # Trace mode (v1.7): wrap client messages with the agent's
        # current logical-clock value before they go on the wire, so the
        # receiving agent can apply the causal-ordering correction.
        # OS messages are never wrapped, mirroring how they're never
        # counted below. No-op (msg goes straight to q.put) when tracing
        # is off for this run.
        if self._trace_dir is not None and not isinstance(msg, _OsMessage):
            ts = self._tick(time.time_ns())
            self._trace_write("sent", outport, msg, ts)
            q.put(_Timestamped(msg, ts))
        else:
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
            # ── Recovery buffer fast path ─────────────────────────
            # During NORMAL or RECORDING (not RECOVER_WAITING), if
            # this inport has buffered channel-state messages from
            # the most recent recovery, serve them in FIFO order
            # before pulling from the queue. The buffer only ever
            # contains client data messages — OS messages are
            # intercepted and never recorded into channel state.
            if (
                self._snapshot_state != _SnapshotState.RECOVER_WAITING
                and self._recovery_buffer.get(inport)
            ):
                msg = self._recovery_buffer[inport].pop(0)
                # Record into ongoing channel-state recording if
                # a snapshot is in progress for this inport.
                with self._snapshot_lock:
                    if (
                        self._snapshot_state == _SnapshotState.RECORDING
                        and self._recording is not None
                        and inport in self._recording["channels"]
                    ):
                        self._recording["channels"][inport].append(msg)
                self.received[inport] += 1
                # Trace mode (v1.7): recovery-buffer messages are plain
                # payloads with no in-flight logical timestamp (the
                # design doc's decided v1 scoping — logical time does
                # not survive a checkpoint/resume). Re-timestamp as if
                # newly arriving, using physical time as the reference.
                if self._trace_dir is not None:
                    ts = self._tick(time.time_ns())
                    self._trace_write("received", inport, msg, ts)
                return msg

            # ── Normal queue read path ───────────────────────────
            msg = q.get()

            # Trace mode (v1.7): unwrap a _Timestamped client message
            # before any of the OS-message dispatch below, so every
            # later branch sees the same plain payload it always has.
            # Only client messages are ever wrapped (see send()), so
            # this can never fire for _GiveMeCounts/_Shutdown/etc.
            _incoming_ts: Optional[int] = None
            if isinstance(msg, _Timestamped):
                _incoming_ts = msg.clock
                msg = msg.payload

            if isinstance(msg, _GiveMeCounts):
                # Respond with current counts — framework handles this.
                # The reply echoes round_id (proving this agent is right
                # now blocked in recv, i.e. passive) and folds in any
                # subclass termination info — a Coordinator reports the
                # inport it will read next as "waiting_on".
                resp = {
                    "agent":    self.name,
                    "sent":     dict(self.sent),
                    "received": dict(self.received),
                    "round_id": getattr(msg, "round_id", None),
                }
                resp.update(self._termination_info())
                self.send_os(resp)

            elif isinstance(msg, _Shutdown):
                # Unwind run() cleanly
                raise _ShutdownSignal()

            elif isinstance(msg, _Checkpoint):
                self._handle_checkpoint(msg, inport)

            elif isinstance(msg, _PrepareRecover):
                self._handle_prepare_recover(msg)

            elif isinstance(msg, _StartRecover):
                self._handle_start_recover(msg)

            else:
                # Client data message.
                # During RECOVER_WAITING, the protocol guarantees no
                # client data should be arriving. Defensively discard
                # any that does, to avoid feeding pre-recovery data
                # to the client.
                if self._snapshot_state == _SnapshotState.RECOVER_WAITING:
                    continue
                # Record into ongoing channel-state recording if
                # snapshot is in progress for this inport.
                with self._snapshot_lock:
                    if (
                        self._snapshot_state == _SnapshotState.RECORDING
                        and self._recording is not None
                        and inport in self._recording["channels"]
                    ):
                        self._recording["channels"][inport].append(msg)
                self.received[inport] += 1
                # Trace mode (v1.7): apply the one clock-update rule —
                # x := max(ref, x+1) — using the sender's timestamp as
                # ref when the message arrived wrapped (the normal
                # case), or physical time if it somehow didn't (e.g. a
                # source's very first message, or tracing turned on
                # mid-flight for an already-in-transit message).
                if self._trace_dir is not None:
                    ref = _incoming_ts if _incoming_ts is not None else time.time_ns()
                    ts = self._tick(ref)
                    self._trace_write("received", inport, msg, ts)
                return msg

    def send_os(self, msg: Any) -> None:
        """
        Send a message directly to os_agent's input queue.
        Used by recv() to respond to _GiveMeCounts.
        Framework use only — not for client code.
        """
        if self.os_q is not None:
            self.os_q.put(msg)

    # ========== Checkpoint-Resume Hooks (v1.6) ==========

    # Convention: the framework constructs one input queue for every
    # source and stores it under this key in self.in_q. Sources poll
    # it via self._poll_os() to receive OS messages (_Checkpoint,
    # _PrepareRecover, _StartRecover). Non-source agents receive OS
    # messages on their normal data inport queues and do not use this
    # key. The leading underscore prevents collision with client
    # inport names.
    _OS_PORT_NAME: str = "_os"

    def save_state(self) -> Any:
        """Return a pickle-safe object capturing every piece of this
        agent's instance state that must survive a snapshot.

        Default: returns an empty dict. Stateless agents need not
        override.

        Stateful agents should override and return a small dict
        containing only *non-derivable* state — position cursors,
        accumulators, debounce timers, per-event counters, RSS
        seen-URL sets, etc. Re-derivable artifacts (loaded ML model
        weights, decoded audio buffers, open file handles) should
        not be saved; they are recreated on first use after resume.

        Called by the framework at most once per snapshot. The agent
        author should ensure save_state is cheap and free of side
        effects.

        Returns
        -------
        A Python object that ``pickle.dumps`` can serialize.
        Typically a dict.
        """
        return {}

    def load_state(self, state: Any) -> None:
        """Restore this agent's state from an object previously
        returned by save_state.

        Default: no-op. Stateful agents override.

        Called by the framework during recovery, before the
        client's recv() returns the first post-recovery message.
        The framework guarantees that no client message has been
        processed by this agent between load_state and the
        subsequent recv() returning the first post-recovery
        message.

        Parameters
        ----------
        state : Any
            Whatever this agent's save_state returned at snapshot
            time. The framework hands it back unchanged via a
            pickle round-trip.
        """
        pass

    def _termination_info(self) -> Dict[str, Any]:
        """Extra fields to include in this agent's _GiveMeCounts reply.

        The base agent adds nothing. A Coordinator overrides this to
        report ``{"waiting_on": <inport>}`` — the single inport it will
        read next, a pure function of its checkpointed state. os_agent
        uses that to disregard messages buffered on the coordinator's
        *other* inports: the coordinator is not reading them and can
        never consume them, so they are not "work remaining" and must
        not hold up termination. Without this, an office with a
        coordinator whose inputs are uneven (a merge_synch with an
        unpaired leftover, a gate waiting on its control inport, a
        select blocked on a reply) would hang forever instead of
        terminating. See os_agent._terminated.
        """
        return {}

    def _poll_os(self, blocking: bool = False, timeout: Optional[float] = None) -> Any:
        """For sources only: poll the OS input queue for one message
        and dispatch it through the appropriate internal handler.

        The framework constructs an input queue for every source and
        stores it at ``self.in_q[Agent._OS_PORT_NAME]``. Sources
        call this method from inside their ``run()`` loop to receive
        OS messages — non-source agents receive OS messages
        transparently through their normal recv() loop and should
        not call this.

        Typical source usage::

            def run(self):
                while True:
                    # ... produce one item of data, emit it ...
                    self._poll_os()                 # non-blocking
                    # while we are in RECOVER_WAITING, stop producing
                    # and just wait for _StartRecover.
                    while self._snapshot_state == _SnapshotState.RECOVER_WAITING:
                        self._poll_os(blocking=True)

        Parameters
        ----------
        blocking : bool
            If True, blocks until an OS message arrives. Used by
            sources in RECOVER_WAITING. If False, returns None when
            the queue is empty (the typical between-iterations poll
            pattern).
        timeout : float | None
            If blocking, maximum seconds to wait. None means wait
            forever.

        Returns
        -------
        The OS message that was processed, or None if the queue was
        empty and blocking is False.
        """
        q = self.in_q.get(Agent._OS_PORT_NAME)
        if q is None:
            return None
        try:
            if blocking:
                msg = q.get(timeout=timeout) if timeout is not None else q.get()
            else:
                msg = q.get_nowait()
        except Empty:
            return None
        # Dispatch by message type. inport is None because this
        # message arrived on the source's dedicated OS input queue,
        # not on a data edge.
        if isinstance(msg, _Checkpoint):
            self._handle_checkpoint(msg, inport=None)
        elif isinstance(msg, _PrepareRecover):
            self._handle_prepare_recover(msg)
        elif isinstance(msg, _StartRecover):
            self._handle_start_recover(msg)
        elif isinstance(msg, _Shutdown):
            raise _ShutdownSignal()
        # _GiveMeCounts also flows here for sources; respond normally
        elif isinstance(msg, _GiveMeCounts):
            self.send_os({
                "agent":    self.name,
                "sent":     dict(self.sent),
                "received": dict(self.received),
                "round_id": getattr(msg, "round_id", None),
            })
        return msg

    def _handle_checkpoint(self, msg: '_Checkpoint', inport: Optional[str]) -> None:
        """Process a _Checkpoint(N) marker. See the algorithm doc for
        the full Chandy-Lamport per-agent algorithm.

        State transitions:
            NORMAL    + first _Checkpoint(N) overall
                          → RECORDING (save state, open all inports
                            except `inport`, forward on outports)
            RECORDING + _Checkpoint(N) on inport β
                          → close β's recording; if all closed,
                            send _Reply(N) and transition to NORMAL.

        For MergeAsynch (multi-worker), the lock serializes all
        access. For single-threaded agents the lock is _NO_LOCK.
        Forwarding may happen more than once per outport
        (at-least-once OK); receivers deduplicate by the
        subsequent-marker rule.

        Parameters
        ----------
        msg : _Checkpoint
            The marker just received.
        inport : str | None
            The inport on which the marker arrived, or None if it
            arrived on a source's OS input queue.
        """
        with self._snapshot_lock:
            # FIRST MARKER OVERALL for snapshot msg.N
            if self._snapshot_state == _SnapshotState.NORMAL:
                self._snapshot_state = _SnapshotState.RECORDING
                self._recording_N = msg.N
                # Snapshot envelope: user state plus framework counters.
                # The wrapping is transparent to the user's save_state /
                # load_state contract. ``_load_checkpoint_from_disk``
                # unwraps and applies sent/received then calls the
                # user's load_state with the inner "user" payload.
                # Old-format snapshots (a bare user dict without "user"
                # key) are still accepted on load.
                saved = {
                    "user":     self.save_state(),
                    "sent":     dict(self.sent),
                    "received": dict(self.received),
                }
                # The inport on which the first marker arrived gets
                # the empty-queue special case (or, if it arrived
                # on a source's OS queue, all data inports are open).
                data_inports = [p for p in self.inports
                                if p != Agent._OS_PORT_NAME]
                if inport is not None and inport in data_inports:
                    open_inports = set(data_inports) - {inport}
                else:
                    open_inports = set(data_inports)
                self._recording = {
                    "saved":        saved,
                    "open_inports": open_inports,
                    "channels":     {p: [] for p in open_inports},
                }
                # Forward on every outport (direct queue.put bypasses
                # the data-message send-count tracking, matching the
                # OS-message convention).
                for outport in self.outports:
                    q = self.out_q.get(outport)
                    if q is not None:
                        q.put(_Checkpoint(N=msg.N))
                # If there are no inports to wait for (sources, or
                # downstream agents whose only inport was the first
                # marker), complete the snapshot immediately.
                if not open_inports:
                    self.send_os(_Reply(
                        N=msg.N, agent=self.name,
                        state=self._recording["saved"],
                        channel_states=self._recording["channels"],
                    ))
                    self._recording = None
                    self._recording_N = None
                    self._snapshot_state = _SnapshotState.NORMAL
                return

            # SUBSEQUENT MARKER for the in-progress snapshot
            if (
                self._snapshot_state == _SnapshotState.RECORDING
                and self._recording_N == msg.N
            ):
                if inport is None:
                    # Duplicate OS broadcast from the OS queue —
                    # ignore.
                    return
                # If this inport's recording is still open, close
                # it now (its channel state was being captured into
                # self._recording["channels"][inport]).
                if inport in self._recording["open_inports"]:
                    self._recording["open_inports"].discard(inport)
                    # Forward on outports (at-least-once OK).
                    for outport in self.outports:
                        q = self.out_q.get(outport)
                        if q is not None:
                            q.put(_Checkpoint(N=msg.N))
                    # All inports closed → snapshot complete for
                    # this agent → reply and reset.
                    if not self._recording["open_inports"]:
                        self.send_os(_Reply(
                            N=msg.N, agent=self.name,
                            state=self._recording["saved"],
                            channel_states=self._recording["channels"],
                        ))
                        self._recording = None
                        self._recording_N = None
                        self._snapshot_state = _SnapshotState.NORMAL
                # else: duplicate marker on an already-closed inport
                # — ignore.
                return

            # _Checkpoint received in RECOVER_WAITING or for a
            # snapshot N other than the one in progress — ignore.
            return

    def _handle_prepare_recover(self, msg: '_PrepareRecover') -> None:
        """Process a _PrepareRecover(N) message.

        Lock-protected and idempotent on duplicate arrivals. On the
        first arrival for snapshot N: abandon any in-flight snapshot
        recording, load checkpoint-N state from disk, populate the
        per-inport recovery buffer, forward _PrepareRecover on every
        outport, send _RecoverReady on os_q, and transition to
        RECOVER_WAITING.
        """
        with self._snapshot_lock:
            # If already in recovery for this or another N, the
            # duplicate is a no-op.
            if self._snapshot_state == _SnapshotState.RECOVER_WAITING:
                return
            # Abandon any in-flight snapshot — recovery wins.
            self._recording = None
            self._recording_N = None
            # Load state and channel-state from disk into the
            # recovery buffer. Done outside the lock would be
            # cleaner, but disk I/O for v1.6's recovery_demo office
            # is small (a single pickle per agent and per inport)
            # and the lock is the no-op singleton for the only
            # agent type that will use this in v1.6 (file_source,
            # custom accumulators — all single-threaded).
            self._load_checkpoint_from_disk(msg.N)
            # Tell the OS manager we are ready, then forward.
            self.send_os(_RecoverReady(N=msg.N, agent=self.name))
            for outport in self.outports:
                q = self.out_q.get(outport)
                if q is not None:
                    q.put(_PrepareRecover(N=msg.N))
            self._snapshot_state = _SnapshotState.RECOVER_WAITING
            self._recovery_N = msg.N

    def _handle_start_recover(self, msg: '_StartRecover') -> None:
        """Process a _StartRecover(N) message.

        Lock-protected and idempotent. Transitions back to NORMAL
        and forwards on every outport. The recovery buffer remains
        populated; subsequent recv() calls serve from it before
        pulling from the inport queue.
        """
        with self._snapshot_lock:
            if self._snapshot_state != _SnapshotState.RECOVER_WAITING:
                # Not in recovery — duplicate or stray; ignore.
                return
            if msg.N != self._recovery_N:
                # Mismatched N — protocol violation; safest to
                # ignore and stay in RECOVER_WAITING until the
                # right one arrives.
                return
            self._snapshot_state = _SnapshotState.NORMAL
            for outport in self.outports:
                q = self.out_q.get(outport)
                if q is not None:
                    q.put(_StartRecover(N=msg.N))
            # _recovery_buffer stays populated — recv() will drain it.

    def _load_checkpoint_from_disk(self, N: int) -> None:
        """Read this agent's checkpoint-N state and per-inport
        channel state from disk and populate self._recovery_buffer.

        Delegates to dissyslab.snapshot for the on-disk layout —
        see that module for the file conventions. For inports with
        no on-disk channel file (e.g. empty channel state at the
        cut), the recovery buffer entry is an empty list — recv()
        then falls through to the queue directly.

        If self._snapshot_dir is None (the office was not started
        with --resume), this is a no-op; the agent does no
        recovery loading.
        """
        if self._snapshot_dir is None:
            return
        from dissyslab.snapshot import load_agent_state, load_channel_state
        state = load_agent_state(self._snapshot_dir, N, self.name)
        if state is not None:
            # v1.6: snapshot envelope is
            #   {"user": <user_state>, "sent": {...}, "received": {...}}
            # See _handle_checkpoint where it is constructed. Old-format
            # snapshots (a bare user dict without "user" key) are still
            # accepted — treat the whole dict as user state.
            if (
                isinstance(state, dict)
                and "user" in state
                and ("sent" in state or "received" in state)
            ):
                if "sent" in state:
                    self.sent.update(state["sent"])
                if "received" in state:
                    self.received.update(state["received"])
                user_state = state["user"]
                if user_state is not None:
                    self.load_state(user_state)
            else:
                # Backward compat: treat whole state as user state.
                self.load_state(state)
        self._recovery_buffer = {}
        for port in self.inports:
            if port == Agent._OS_PORT_NAME:
                continue
            self._recovery_buffer[port] = load_channel_state(
                self._snapshot_dir, N, self.name, port
            )

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
