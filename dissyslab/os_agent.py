# dissyslab/os_agent.py
"""
OsAgent: Termination detector for DSL networks.

OsAgent runs alongside the client network and declares termination when:
  (1) every agent is idle and said so this round (or has reported that
      it will never be active again), AND
  (2) for every reachable edge, sent count == received count.

**active** means the agent has an outstanding obligation -- it will send
at some future point without needing to receive anything first.
**idle** is the negation. Every agent reports which it is; os_agent does
not classify agents by kind, so a new kind of agent needs no change here.

How agents come to answer differs, though:

  Sources (no inports):
    Cannot be polled -- they are not sitting in recv where a poll could
    reach them. A source sends ONE message to os_agent when its run()
    completes, carrying its final counts and ``final=True``.

  Agents with inports:
    Polled periodically via _GiveMeCounts, which is intercepted inside
    recv. They respond with current counts, their idle bit, and the
    round they are answering. os_agent does NOT wait for all responses
    per cycle -- it drains whatever has arrived.

    For a *reactive* agent -- one that sends only in response to a
    message -- answering is itself the proof of idleness, since recv is
    the only place it can answer from and there it owes nothing. For a
    *non-reactive* agent with its own thread of control, such as an
    Alarm, answering proves nothing and the idle bit carries the weight.

See docs/internals/reference/os_agent_overview.md for the full picture and
docs/internals/design/termination_detection_design.md for the design.

OsAgent is created automatically by network.py during compilation.
It is not part of the user's network — it is a framework component.

Communication:
  Sources     → OsAgent: one termination message via send_os() when done
  OsAgent     → non-sources: _GiveMeCounts into client's inport queue
  Non-sources → OsAgent: count response via send_os()
  OsAgent     → non-sources: _Shutdown into client's inport queue
"""

from __future__ import annotations
from queue import SimpleQueue, Empty
from typing import Dict, List, Tuple, Any, Set, Optional
from pathlib import Path
import sys
import threading
import time

from dissyslab.core import (
    _GiveMeCounts, _Shutdown,
    _Checkpoint, _Reply, _PrepareRecover, _RecoverReady, _StartRecover,
)


class OsAgent:
    """
    Termination detector for a compiled DSL network.

    Args:
        agents:            Dict mapping agent name → agent instance (flattened)
        graph_connections: List of (from_agent, from_port, to_agent, to_port)
        poll_interval:     Seconds between poll cycles (default 0.1)
    """

    def __init__(
        self,
        agents: Dict[str, Any],
        graph_connections: List[Tuple[str, str, str, str]],
        poll_interval: float = 0.1,
        # ── Checkpoint-resume parameters (v1.6) ──────────────────
        snapshot_interval: Optional[float] = None,
        snapshot_dir: Optional[Path] = None,
        office_name: str = "office",
    ):
        self.all_agents = dict(agents)
        self.graph_connections = list(graph_connections)
        self.poll_interval = poll_interval
        # Set by Network._stop_all_agents on the timeout path. The
        # loop below exits only when it declares termination, which is
        # by definition not what happened at a timeout -- so without
        # this the manager thread outlives every agent it manages and
        # the process still cannot exit.
        self._stop_event = threading.Event()

        # Input queue — all agents post messages here via send_os()
        self.in_q = SimpleQueue()

        # Separate sources (no inports) from non-sources (have inports)
        self.source_agents:     Set[str] = set()
        self.non_source_agents: Set[str] = set()

        # client_queues populated by network._wire_os_agent_queues()
        # after _wire_queues() has created all inport queues
        self.client_queues: Dict[str, Any] = {}

        for name, agent in self.all_agents.items():
            if not agent.inports:
                self.source_agents.add(name)
            else:
                self.non_source_agents.add(name)

        # ── Activity, as reported by each agent ──────────────────────
        # ``idle`` is what an agent said in its most recent reply.
        # ``final`` is sticky and means "will never be active again" —
        # how an exhausted Source tells os_agent to stop waiting for
        # replies from a thread that has ended.
        #
        # Reading these instead of classifying agents by kind is what
        # keeps the detector closed to modification. An Alarm, an agent
        # with an HTTP request in flight, or a kind nobody has written
        # yet reports its own activity, and os_agent needs no branch for
        # it. See docs/internals/design/termination_detection_design.md §3.
        self.idle:  Dict[str, bool] = {}
        self.final: Set[str] = set()

        # ── Passivity + coordinator tracking (coordinator TD fix, #47) ──
        # Monotonic poll-round counter. Each poll cycle bumps it and
        # stamps every _GiveMeCounts with it; an agent's reply echoes the
        # round it answered. A reply for the current round proves the
        # answer is *current* — an agent mid-computation cannot have sent
        # it. That is a separate fact from the idle bit above, and both
        # are required: the round tag says "recently", the bit says
        # "owes nothing".
        self._round: int = 0
        self._round_responded: Dict[str, int] = {}
        # For each coordinator, the inport it will read next (from its
        # reply's "waiting_on"). Absent for ordinary agents, which must
        # have *every* inport empty to be considered done.
        self.waiting_on: Dict[str, str] = {}

        # Edge counts — latest known values from any received messages
        # Keyed by (agent_name, port_name)
        self.edge_sent:     Dict[Tuple[str, str], int] = {}
        self.edge_received: Dict[Tuple[str, str], int] = {}
        for (fa, fp, ta, tp) in self.graph_connections:
            self.edge_sent[(fa, fp)] = 0
            self.edge_received[(ta, tp)] = 0

        # ── Checkpoint-resume state (v1.6) ───────────────────────
        # See docs/algorithms/CHECKPOINT_RESUME.md.
        self.snapshot_interval: Optional[float] = snapshot_interval
        self.snapshot_dir: Optional[Path] = snapshot_dir
        self.office_name: str = office_name

        # Monotonic snapshot number. Incremented every time a snapshot
        # is initiated, whether periodic or manual.
        self._next_N: int = 0

        # Wall-clock time after which the next periodic snapshot fires.
        # Sentinel float('inf') means periodic snapshots are disabled.
        self._next_snapshot_at: float = (
            time.time() + snapshot_interval
            if snapshot_interval is not None
            else float("inf")
        )

        # In-flight snapshot bookkeeping. Keyed by N.
        # _inflight_checkpoints[N] = {
        #     "pending": set of agent names yet to reply,
        #     "replies": dict of agent_name → _Reply,
        # }
        self._inflight_checkpoints: Dict[int, Dict[str, Any]] = {}

        # In-flight recovery bookkeeping. Either None (no recovery
        # underway) or a dict:
        # _inflight_recovery = {
        #     "N":       snapshot number being recovered,
        #     "pending": set of agent names yet to send _RecoverReady,
        # }
        self._inflight_recovery: Optional[Dict[str, Any]] = None

        # Source OS input queues, keyed by source agent name. Populated
        # by network.py in Part C after _wire_queues completes. The
        # OS manager uses these to put _Checkpoint, _PrepareRecover,
        # and _StartRecover messages directly into each source's input
        # queue, from which they propagate via upstream-forwarding to
        # the rest of the network.
        self._source_os_inports: Dict[str, Any] = {}

    # ── Main loop ─────────────────────────────────────────────────────────────

    def run(self) -> None:
        """
        Poll non-source agents periodically. Drain any messages that have
        arrived (from sources or non-sources). Declare termination when
        all agents heard from and all edges balanced. Then shut down all
        non-source agents.

        v1.6 extension: when ``snapshot_interval`` is set, the loop also
        initiates a periodic snapshot every ``snapshot_interval`` seconds
        and drains _Reply / _RecoverReady messages from in_q alongside
        the existing count responses.
        """
        while True:
            if self._stop_event.is_set():
                return
            # Send this round's poll, THEN wait, THEN collect — so the
            # replies we drain answer the round we just sent. That lets
            # the passivity check (reply round == current round) mean
            # "this agent is blocked in recv right now."
            self._send_give_me_counts()
            # wait() rather than sleep() so a stop request is noticed
            # immediately instead of after the rest of this poll cycle.
            if self._stop_event.wait(self.poll_interval):
                return
            self._drain_responses()

            # Periodic snapshot trigger (v1.6).
            if time.time() >= self._next_snapshot_at:
                self._initiate_snapshot(self._next_N)
                self._next_N += 1
                self._next_snapshot_at = (
                    time.time() + self.snapshot_interval
                )

            if self._terminated():
                self._shutdown_all()
                return

    # ── Polling ───────────────────────────────────────────────────────────────

    def _send_give_me_counts(self) -> None:
        """
        Poll every non-source agent for its counts, tagging this round.

        Sends to *all* of an agent's inport queues, not just the first.
        A coordinator blocks on whichever inport its state selects, so a
        poll placed only on inport[0] would never be seen while it waits
        on a different inport — and we would never learn it is stuck.
        Putting one _GiveMeCounts on every inport guarantees the agent
        reads it from whichever inport it is currently blocked on,
        replies (echoing this round), and blocks again. (_GiveMeCounts is
        an OS message: intercepted in recv, never counted, never recorded
        into channel state.)
        """
        self._round += 1
        msg = _GiveMeCounts(round_id=self._round)
        for name, queues in self.client_queues.items():
            for q in queues:
                q.put(msg)

    def _drain_responses(self) -> None:
        """
        Drain all messages currently in in_q without blocking.
        Dispatches by message type:

        - _Reply           → _collect_reply (snapshot replies)
        - _RecoverReady    → _collect_recover_ready (recovery handshake)
        - dict             → _update_counts (existing termination format)
        """
        while True:
            try:
                response = self.in_q.get_nowait()
            except Empty:
                break
            if isinstance(response, _Reply):
                self._collect_reply(response)
            elif isinstance(response, _RecoverReady):
                self._collect_recover_ready(response)
            else:
                # Existing count-response format: dict with agent/sent/received.
                self._update_counts(response)

    # ── Count updates ─────────────────────────────────────────────────────────

    def _update_counts(self, response: Dict) -> None:
        """
        Update edge counts from any agent's message.

        Message format (same for sources and non-sources):
            {
                "agent":    agent_name,
                "sent":     {port_name: count, ...},
                "received": {port_name: count, ...},
            }
        """
        agent_name = response["agent"]

        # Passivity: record which poll round this reply answers. A reply
        # for the current round means the agent is blocked in recv now.
        rid = response.get("round_id")
        if rid is not None:
            self._round_responded[agent_name] = rid

        # Activity. The default for a missing "idle" is **False**, not
        # True: an agent whose reply does not say is treated as active,
        # so a kind that forgets to report delays termination rather
        # than causing a premature one. See the conservative-default
        # rule in Agent.is_idle.
        self.idle[agent_name] = bool(response.get("idle", False))
        if response.get("final"):
            self.final.add(agent_name)      # sticky

        # Coordinators report the inport they will read next.
        if "waiting_on" in response:
            self.waiting_on[agent_name] = response["waiting_on"]

        for port, count in response["sent"].items():
            key = (agent_name, port)
            if key in self.edge_sent:
                self.edge_sent[key] = count

        for port, count in response["received"].items():
            key = (agent_name, port)
            if key in self.edge_received:
                self.edge_received[key] = count

    # ── Termination check ─────────────────────────────────────────────────────

    def _terminated(self) -> bool:
        """
        Return True iff the office is quiescent — no message anywhere can
        be received by any agent, so no further progress is possible.

        Two conditions, all required:

        (1) **Every agent is idle, and said so recently.** For each
            agent, either it has reported ``final`` — it will never be
            active again, which is how an exhausted source bows out —
            or its most recent reply answered *this* poll round and
            said ``idle``.

            Both halves are needed and they do different jobs. The
            **round tag** proves the reply is current: a reactive agent
            that is mid-processing does not reply at all, and without
            the tag its previous reply — which said ``idle``, because it
            was sent from inside ``recv`` — would be believed while the
            agent is busy. The **idle bit** says whether the agent owes
            a future send, which the round tag cannot establish for a
            non-reactive agent, since a Source or an Alarm can reply
            while active.

            This replaces the older formulation of "sources exhausted
            plus every non-source passive". That worked, but it named
            the two kinds of agent that existed rather than the property
            they differ on, so every new kind meant another branch here.
            See docs/internals/design/termination_detection_design.md.

        (2) **Every reachable channel is empty.** For an ordinary agent,
            *every* inbound channel must be empty (it reads its one inbox
            unconditionally, so anything buffered there is live work). For
            a **coordinator**, only the channel into the inport it is
            waiting on must be empty; messages buffered on its *other*
            inports are unreachable from where it stands and do not count
            (this is the coordinator fix — otherwise a merge_synch with an
            unpaired leftover, or a gate/select blocked elsewhere, hangs
            forever). ``waiting_on`` names that inport; absent for
            ordinary agents, so the strict rule applies to them.
        """
        # (1) every agent idle, and said so this round (or is final).
        for name in self.all_agents:
            if name in self.final:
                continue                       # permanently idle
            if self._round_responded.get(name) != self._round:
                return False                   # not a current answer
            if not self.idle.get(name, False):
                return False                   # active

        # (2) every reachable channel empty.
        for (fa, fp, ta, tp) in self.graph_connections:
            sent = self.edge_sent.get((fa, fp), 0)
            received = self.edge_received.get((ta, tp), 0)
            if sent == received:
                continue                       # channel empty — fine
            waiting = self.waiting_on.get(ta)  # None for ordinary agents
            if waiting is not None and waiting != tp:
                continue                       # buffered on a coordinator
                                               # inport it is not reading →
                                               # unreachable, not live work
            return False                       # a reachable channel is nonempty

        return True

    # ── Shutdown ──────────────────────────────────────────────────────────────

    def request_stop(self) -> None:
        """Ask the manager loop to return at its next opportunity.

        Used on the timeout path, where ``_terminated()`` is false by
        definition and the loop would otherwise never end.
        """
        self._stop_event.set()

    def _shutdown_all(self) -> None:
        """
        Send _Shutdown to all non-source agents.
        Sends to ALL inport queues so every worker thread exits cleanly.
        (MergeAsynch has one worker thread per inport — each needs _Shutdown.)
        """
        msg = _Shutdown()
        for name, queues in self.client_queues.items():
            for q in queues:
                q.put(msg)

    # ── Checkpoint-Resume Orchestration (v1.6) ────────────────────────────
    # See docs/algorithms/CHECKPOINT_RESUME.md for the full specification.
    # The OS manager initiates snapshots and recoveries by putting
    # messages directly into source input queues; the messages
    # propagate via upstream-forwarding through the rest of the network.

    def _broadcast_to_sources(self, msg: Any) -> None:
        """Put a message in every source's OS input queue.

        Source agents poll the queue from inside their run() loop
        via Agent._poll_os() and execute the appropriate snapshot or
        recovery handler when the message arrives. The handler then
        forwards the same message on every outport, which is how it
        propagates downstream.
        """
        for name, q in self._source_os_inports.items():
            q.put(msg)

    # ── Snapshot initiation and reply collection ─────────────────────────

    def _initiate_snapshot(self, N: int) -> None:
        """Start snapshot N by broadcasting _Checkpoint(N) to all source
        input queues.

        Records the in-flight bookkeeping so that _collect_reply can
        decide when all agents have replied and the snapshot is
        complete.
        """
        if not self._source_os_inports:
            # No sources wired up — cannot initiate a snapshot. This
            # happens before network.py finishes Phase 2; ignore.
            return
        self._inflight_checkpoints[N] = {
            "pending": set(self.all_agents.keys()),
            "replies": {},
        }
        self._broadcast_to_sources(_Checkpoint(N=N))

    def _collect_reply(self, reply: '_Reply') -> None:
        """Record one agent's snapshot reply. When the last reply for
        snapshot N arrives, write the snapshot to disk and clear the
        in-flight tracking."""
        inflight = self._inflight_checkpoints.get(reply.N)
        if inflight is None:
            # Stray or late reply for a snapshot that has already
            # been written or abandoned. Drop silently.
            return
        inflight["replies"][reply.agent] = reply
        inflight["pending"].discard(reply.agent)
        if not inflight["pending"]:
            try:
                self._write_snapshot(reply.N, inflight["replies"])
            except Exception as exc:
                print(
                    f"[os_agent] snapshot {reply.N} write failed: {exc}",
                    file=sys.stderr,
                )
            del self._inflight_checkpoints[reply.N]

    def _write_snapshot(self, N: int, replies: Dict[str, '_Reply']) -> None:
        """Persist snapshot N to disk under self.snapshot_dir.

        Delegates to dissyslab.snapshot.write_snapshot which owns
        the on-disk layout and naming conventions (see that module
        for the full specification).
        """
        if self.snapshot_dir is None:
            return  # in-memory only mode
        from dissyslab.snapshot import write_snapshot
        write_snapshot(
            snapshot_dir=self.snapshot_dir,
            office_name=self.office_name,
            N=N,
            graph_connections=self.graph_connections,
            replies=replies,
        )

    # ── Recovery initiation and handshake ─────────────────────────────────

    def initiate_recovery(self, N: int) -> None:
        """Start the four-way recovery handshake for snapshot N.

        Step 1: broadcast _PrepareRecover(N) to all source input queues.
        Step 2: each agent loads checkpoint-N state and sends _RecoverReady.
        Step 3 (in _collect_recover_ready): once all _RecoverReady are in,
                broadcast _StartRecover(N) to all source input queues.
        Step 4: each agent forwards _StartRecover and resumes execution.

        Recovery wins over any in-flight snapshot: existing
        _inflight_checkpoints are cleared (agents abandon their
        RECORDING state when they see _PrepareRecover).
        """
        # Abandon any in-flight snapshots.
        self._inflight_checkpoints.clear()
        # Track the recovery handshake.
        self._inflight_recovery = {
            "N":       N,
            "pending": set(self.all_agents.keys()),
        }
        self._broadcast_to_sources(_PrepareRecover(N=N))

    def _collect_recover_ready(self, ready: '_RecoverReady') -> None:
        """Record one agent's _RecoverReady. When the last one arrives,
        broadcast _StartRecover to release the barrier."""
        if self._inflight_recovery is None:
            # Stray RecoverReady — no recovery underway.
            return
        if ready.N != self._inflight_recovery["N"]:
            # Wrong snapshot number — ignore.
            return
        self._inflight_recovery["pending"].discard(ready.agent)
        if not self._inflight_recovery["pending"]:
            # All agents have loaded state and are awaiting StartRecover.
            self._broadcast_to_sources(_StartRecover(N=ready.N))
            self._inflight_recovery = None


# Module-level helpers (filename sanitization, etc.) live in
# dissyslab.snapshot now.
