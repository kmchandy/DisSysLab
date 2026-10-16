"""The operating system's part of every agent.

``Agent`` (:mod:`dissyslab.runtime.agent`) inherits from ``OsHooks``.
Everything here is done *by the framework* on the agent's own thread, out
of the role's sight, and is described in the algorithm documents:

- **termination detection**: answering the detector's polls
  (``is_idle``, ``is_final``, ``_termination_info``, ``send_os``);
  ``docs/internals/design/termination_detection_design.md``;
- **snapshots and recovery** (Chandy-Lamport): markers, channel-state
  recording, loading a checkpoint (``_handle_checkpoint`` and the
  recovery handlers); ``docs/algorithms/CHECKPOINT_RESUME.md``;
- **tracing**: the hybrid logical clock and the trace files
  (``_tick``, ``_trace_write``); ``docs/algorithms/TRACE_AND_LOGICAL_CLOCK.md``.

``Agent.send`` and ``Agent.recv`` call the ``_os_*`` methods at the end of
this file; each call is one named step, so a reader of ``agent.py`` sees
exactly where the operating system steps in.

The algorithm code was moved here unchanged from ``dissyslab/core.py``
(restructure_plan.md, Phase 1); only the six ``_os_*`` helpers are new,
and each holds lines that used to sit inline in ``send`` or ``recv``.
This module is on the mypy debt list until the OS algorithms are revisited.
"""

from __future__ import annotations

import json
import time
from enum import Enum
from pathlib import Path
from queue import Empty
from typing import Any, Dict, List, Optional, Tuple

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
    _Timestamped,
)


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


class OsHooks:
    """The operating system's state and handlers, inherited by ``Agent``."""

    # Set by Agent.__init__ before _os_init is called.
    name: Optional[str]
    inports: List[str]
    outports: List[str]
    in_q: Dict[str, Any]
    out_q: Dict[str, Any]
    sent: Dict[str, int]
    received: Dict[str, int]
    os_q: Any

    def _os_init(self) -> None:
        """Create the operating system's bookkeeping for this agent."""
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

    def send_os(self, msg: Any) -> None:
        """
        Send a message directly to os_agent's input queue.
        Used by recv() to respond to _GiveMeCounts.
        Framework use only — not for client code.
        """
        if self.os_q is not None:
            self.os_q.put(msg)

    # Convention: the framework constructs one input queue for every
    # source and stores it under this key in self.in_q. Sources poll
    # it via self._poll_os() to receive OS messages (_Checkpoint,
    # _PrepareRecover, _StartRecover). Non-source agents receive OS
    # messages on their normal data inport queues and do not use this
    # key. The leading underscore prevents collision with client
    # inport names.
    _OS_PORT_NAME: str = "_os"

    # ── Activity, for termination detection ───────────────────────────────
    #
    # The standard vocabulary: an agent is **active** when it has an
    # outstanding obligation -- it will send at some future point without
    # needing to receive anything first -- and **idle** otherwise.
    #
    # The two kinds of agent differ in how idleness can be *known*, and
    # that asymmetry is the whole of the design:
    #
    #   A **reactive** agent sends only in response to a message. It can
    #   only answer a poll from inside recv(), where by construction it
    #   owes nothing -- so answering is itself the proof of idleness, and
    #   the base implementation below can simply return True.
    #
    #   A **non-reactive** agent -- a Source, an Alarm, anything with its
    #   own thread of control -- can answer a poll while active.
    #   Answering proves nothing, so it must override these and report.
    #
    # See docs/internals/design/termination_detection_design.md.

    def is_idle(self) -> bool:
        """True when this agent owes no future send.

        Constant ``True`` for a reactive agent: the only place it can
        answer a poll is inside ``recv``, and there it owes nothing.
        Redundant, and worth paying for the uniformity -- os_agent then
        reads one field for every agent instead of classifying by kind,
        and a new kind of agent needs no change to the detector.

        **Override conservatively.** Report active unless you can prove
        you owe nothing. A false ``idle`` terminates the office early and
        silently discards work; a false ``active`` only delays the
        verdict. That asymmetry is what makes new agent kinds safe to
        add: an author who has never read the detector gets it right if
        the default errs active.

        **Define idleness over messages processed, not over the world.**
        An Alarm is idle iff it has not yet *received* its worker's
        finished message -- not iff the worker has finished. The two
        differ for the microseconds that message is in flight, and the
        message-based definition errs conservative and makes the agent's
        state a function of its own message history, which is what makes
        it snapshottable at all.
        """
        return True

    def is_final(self) -> bool:
        """True when this agent will never be active again.

        A final agent stops replying -- an exhausted Source ends its
        thread -- so os_agent records it as permanently idle and stops
        expecting fresh replies. Without this, "gone" and "slow" are the
        same observation.

        A Source is final when exhausted; a reactive agent is final only
        at shutdown, so the base returns False.
        """
        return False

    def _handle_os_extension(self, msg: Any, inport: str) -> bool:
        """Let a subclass handle an OS message kind of its own.

        Return ``True`` if the message was recognised and handled, in
        which case ``recv`` continues waiting; ``False`` to let it fall
        through to the client-data path. The base recognises nothing.

        This is the incoming counterpart to ``_termination_info``, which
        lets a subclass extend the poll *reply*. ``Alarm`` uses it to
        catch ``_TimerFired``.

        The alternative — a subclass reading its queue directly instead
        of calling ``recv`` — was rejected. ``recv`` is not a thin
        wrapper: it handles the recovery-buffer fast path, the logical
        clock, four OS message kinds, the RECOVER_WAITING discard,
        snapshot channel-state recording under a lock, and counting. A
        second implementation would diverge the first time any of those
        changed, and the symptom would be a corrupted cut rather than a
        wrong number.

        Note that a handler runs on the agent's own thread, which is
        what lets ``Alarm`` do its sending from here.
        """
        return False

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
        stores it at ``self.in_q[self._OS_PORT_NAME]``. Sources
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
        q = self.in_q.get(self._OS_PORT_NAME)
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
                                if p != self._OS_PORT_NAME]
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
            if port == self._OS_PORT_NAME:
                continue
            self._recovery_buffer[port] = load_channel_state(
                self._snapshot_dir, N, self.name, port
            )

    # save_state and load_state are defined on Agent; the handlers above
    # call them through self.

    # ========== Steps called from Agent.send and Agent.recv ==========

    def _os_wrap_outgoing(self, msg: Any, outport: str) -> Any:
        """What actually goes on the queue for ``msg``.

        With tracing on, an office message is stamped with this agent's
        logical clock, written to the trace, and wrapped; otherwise it
        goes as it is. OS messages are never wrapped.
        """
        if self._trace_dir is not None and not isinstance(msg, _OsMessage):
            ts = self._tick(time.time_ns())
            self._trace_write("sent", outport, msg, ts)
            return _Timestamped(msg, ts)
        return msg

    def _os_take_recovered(self, inport: str) -> Tuple[bool, Any]:
        """After a resume, the messages that were in transit at the snapshot.

        Returns ``(True, msg)`` while the recovery buffer for ``inport``
        still holds messages (outside RECOVER_WAITING), recording the
        message into an in-progress snapshot as if it had just arrived;
        ``(False, None)`` otherwise.
        """
        if (
            self._snapshot_state != _SnapshotState.RECOVER_WAITING
            and self._recovery_buffer.get(inport)
        ):
            msg = self._recovery_buffer[inport].pop(0)
            with self._snapshot_lock:
                if (
                    self._snapshot_state == _SnapshotState.RECORDING
                    and self._recording is not None
                    and inport in self._recording["channels"]
                ):
                    self._recording["channels"][inport].append(msg)
            return True, msg
        return False, None

    def _os_unwrap(self, msg: Any) -> Tuple[Any, Optional[int]]:
        """Remove a tracing wrapper: ``(message, sender's clock or None)``."""
        if isinstance(msg, _Timestamped):
            return msg.payload, msg.clock
        return msg, None

    def _os_intercept(self, msg: Any, inport: str) -> bool:
        """Handle ``msg`` if it is an operating-system message.

        Returns True when it was one (the caller keeps waiting), False for
        an office message. A ``_Shutdown`` raises ``_ShutdownSignal``.
        """
        if isinstance(msg, _GiveMeCounts):
            # The reply echoes round_id (proving this agent is right now
            # blocked in recv, i.e. passive) and folds in any subclass
            # termination info -- a Coordinator reports the inport it
            # will read next as "waiting_on".
            resp = {
                "agent":    self.name,
                "sent":     dict(self.sent),
                "received": dict(self.received),
                "round_id": getattr(msg, "round_id", None),
                "idle":     self.is_idle(),
                "final":    self.is_final(),
            }
            resp.update(self._termination_info())
            self.send_os(resp)
            return True
        if isinstance(msg, _Shutdown):
            raise _ShutdownSignal()
        if isinstance(msg, _Checkpoint):
            self._handle_checkpoint(msg, inport)
            return True
        if isinstance(msg, _PrepareRecover):
            self._handle_prepare_recover(msg)
            return True
        if isinstance(msg, _StartRecover):
            self._handle_start_recover(msg)
            return True
        return self._handle_os_extension(msg, inport)

    def _os_accept(self, msg: Any, inport: str) -> bool:
        """Whether an office message may be handed to the role.

        During RECOVER_WAITING the protocol guarantees no office data
        arrives; any that does is discarded rather than fed to the role.
        Otherwise the message is recorded into an in-progress snapshot.
        """
        if self._snapshot_state == _SnapshotState.RECOVER_WAITING:
            return False
        with self._snapshot_lock:
            if (
                self._snapshot_state == _SnapshotState.RECORDING
                and self._recording is not None
                and inport in self._recording["channels"]
            ):
                self._recording["channels"][inport].append(msg)
        return True

    def _os_trace_received(self, inport: str, msg: Any, incoming_ts: Optional[int]) -> None:
        """With tracing on, advance the clock for a receive and log it.

        The one clock rule, x := max(ref, x + 1), uses the sender's
        timestamp as ref, or physical time when there is none (a message
        replayed after a resume, or one sent before tracing was on).
        """
        if self._trace_dir is not None:
            ref = incoming_ts if incoming_ts is not None else time.time_ns()
            ts = self._tick(ref)
            self._trace_write("received", inport, msg, ts)
