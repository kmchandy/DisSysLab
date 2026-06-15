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
            time.sleep(self.poll_interval)
            self._send_give_me_counts()
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
        Send _GiveMeCounts to all non-source agents.
        Sends to the first inport queue only — one worker picks it up
        and responds with the agent's full counts.
        """
        msg = _GiveMeCounts()
        for name, queues in self.client_queues.items():
            queues[0].put(msg)

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
        Return True iff:
          (1) heard from every agent (sources via termination msg,
              non-sources via at least one _GiveMeCounts response), AND
          (2) all edges balanced: sent == received on every edge.
        """
        if self.heard_from != set(self.all_agents.keys()):
            return False

        for (fa, fp, ta, tp) in self.graph_connections:
            sent = self.edge_sent.get((fa, fp), 0)
            received = self.edge_received.get((ta, tp), 0)
            if sent != received:
                return False

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
