# dissyslab/os_agent.py
"""
OsAgent: Termination detector for DSL networks.

OsAgent runs alongside the client network and declares termination when:
  (1) every agent has been heard from, AND
  (2) for every edge, sent count == received count.

Two kinds of agents are handled differently:

  Sources (no inports):
    Cannot be polled. Instead, a source sends ONE termination message to
    os_agent when its run() method completes. The message contains the
    source's final sent counts.

  Non-source agents (have inports):
    Polled periodically via _GiveMeCounts. They respond with current
    sent/received counts via send_os(). os_agent does NOT wait for all
    responses per cycle — it drains whatever has arrived and uses the
    latest known counts.

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

        # heard_from: agents os_agent has received at least one message from
        self.heard_from: Set[str] = set()

        # ── Passivity + coordinator tracking (coordinator TD fix, #47) ──
        # Monotonic poll-round counter. Each poll cycle bumps it and
        # stamps every _GiveMeCounts with it; an agent's reply echoes the
        # round it answered. When a non-source agent's latest reply is for
        # the current round, that agent is *right now* blocked in recv —
        # i.e. passive. All non-sources passive + reachable channels empty
        # + sources exhausted == termination.
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
            # Send this round's poll, THEN wait, THEN collect — so the
            # replies we drain answer the round we just sent. That lets
            # the passivity check (reply round == current round) mean
            # "this agent is blocked in recv right now."
            self._send_give_me_counts()
            time.sleep(self.poll_interval)
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
        self.heard_from.add(agent_name)

        # Passivity: record which poll round this reply answers. A reply
        # for the current round means the agent is blocked in recv now.
        rid = response.get("round_id")
        if rid is not None:
            self._round_responded[agent_name] = rid
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

        Three conditions, all required:

        (1) **Sources exhausted.** Every agent has been heard from; a
            source is heard from only when it finishes and sends its
            termination message, so this subsumes "no new external input."

        (2) **Every non-source agent is passive** — blocked in recv right
            now. We know this because its most recent reply answered the
            current poll round: an agent that is mid-processing (not in
            recv) cannot have answered this round's _GiveMeCounts. This
            guards against a false "done" while, say, an LLM worker is
            still thinking with balanced counts.

        (3) **Every reachable channel is empty.** For an ordinary agent,
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
        # (1) sources exhausted / everyone heard from.
        if self.heard_from != set(self.all_agents.keys()):
            return False

        # (2) every non-source agent is currently passive (answered this round).
        for name in self.non_source_agents:
            if self._round_responded.get(name) != self._round:
                return False

        # (3) every reachable channel empty.
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
