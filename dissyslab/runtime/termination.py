# dissyslab/runtime/termination.py (formerly dissyslab/os_agent.py)
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

OsAgent is created automatically by runtime/network.py during compilation.
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

from dissyslab.runtime.messages import (
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

        # ── Stalls (spec 4.5, item 6) ─────────────────────────────────
        # What each agent holds, from its reply's "holding": work it has
        # taken in and cannot finish until something arrives on the
        # inboxes in "needs" (a gate's admitted item, a synchronizer's
        # incomplete group). The stall walk starts from these.
        self.holding: Dict[str, Dict[str, Any]] = {}
        # holder -> the report, once a stall is declared (never retracted:
        # a stall is stable, like termination).
        self.stalls: Dict[str, List[str]] = {}
        # holder -> what the walk found last round; a stall found while the
        # office is still running is declared only when two consecutive
        # rounds agree (see _find_stalls).
        self._stall_last: Dict[str, Any] = {}
        # (agent, inbox) -> (agent, outbox) of the one connection into it.
        # The network keeps one connection per inbox (fan-in goes through
        # an inserted merge agent), so the walk back is unambiguous.
        self._feeds: Dict[Tuple[str, str], Tuple[str, str]] = {
            (ta, tp): (fa, fp) for (fa, fp, ta, tp) in graph_connections
        }

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
                # Quiescence is proven, so every holder is stuck for good:
                # no second round is needed to confirm it.
                self._find_stalls(confirm=False)
                self._shutdown_all()
                return
            self._find_stalls(confirm=True)

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

        # Held work, if any (gate, synchronizer); absent means none.
        if "holding" in response:
            self.holding[agent_name] = response["holding"]
        else:
            self.holding.pop(agent_name, None)

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

    # ── Stalls ────────────────────────────────────────────────────────────────

    def _current_idle(self, name: str) -> bool:
        """Idle, and said so in answer to this round's poll."""
        return self._round_responded.get(name) == self._round and self.idle.get(name, False)

    def _waits_on(self, name: str) -> List[str]:
        """The inboxes ``name`` is reading: its ``waiting_on``, or all of them."""
        if name in self.waiting_on:
            return [self.waiting_on[name]]
        return list(self.all_agents[name].inports)

    def _stall_walk(self, holder: str) -> Optional[Tuple[Any, List[Tuple[str, ...]]]]:
        """Walk back from what ``holder`` needs. The stall it proves, or None.

        From each inbox the holder needs, follow the one connection into
        it to the agent and outbox that feed it. If the connection is
        empty and that agent is idle, follow every inbox *it* is reading,
        and so on. A branch ends at an agent already on the walk (a
        cycle) or at a finished source. The walk fails -- the holder may
        yet be released -- at a connection that holds a message, or at an
        agent that is busy or has not answered this round (which includes
        a source that is still producing).

        If no branch fails, the agents visited form a closed set S: each
        idle, every connection into S empty, and every connection into S
        from S itself or from a finished source. Nothing in S can be
        woken except by a message sent from S, and nothing in S can send:
        the termination condition, applied to S instead of the whole
        office. The holder never gets what it needs.

        Returns (a signature of what was observed, the edges walked), or
        None.
        """
        info = self.holding.get(holder)
        if not info or not self._current_idle(holder):
            return None
        visited = {holder}
        edges: List[Tuple[str, ...]] = []
        observed: List[Tuple[str, str, int]] = []
        frontier = [(holder, inbox) for inbox in info.get("needs", [])]
        while frontier:
            to, inbox = frontier.pop(0)
            feed = self._feeds.get((to, inbox))
            if feed is None:
                edges.append((to, inbox, "", "", "nothing is connected to it"))
                continue
            frm, outbox = feed
            sent = self.edge_sent.get((frm, outbox), 0)
            if sent != self.edge_received.get((to, inbox), 0):
                return None                    # a message is on its way
            observed.append((frm, outbox, sent))
            if frm in self.final:
                edges.append((to, inbox, frm, outbox, f"{frm} has finished"))
            elif frm in visited:
                edges.append((to, inbox, frm, outbox, f"{frm} is already on this path"))
            elif not self._current_idle(frm):
                return None                    # busy, or has not answered
            else:
                visited.add(frm)
                waits = self._waits_on(frm)
                edges.append((to, inbox, frm, outbox,
                              f"{frm} is idle, waiting on {', '.join(map(_port, waits))}"))
                frontier.extend((frm, w) for w in waits)
        return (frozenset(visited), tuple(observed)), edges

    def _find_stalls(self, confirm: bool) -> None:
        """Declare every holder whose walk proves it stuck (``_stall_walk``).

        While the office is running (``confirm``), a stall is declared only
        when the walk finds the same agents and the same counts in two
        consecutive rounds. Each round's replies arrive at slightly
        different times; agreement across two rounds rules out a reading
        taken while a message was passing between two agents. At
        termination, quiescence is already proven, so one walk suffices.
        """
        seen: Dict[str, Any] = {}
        for holder in list(self.holding):
            if holder in self.stalls:
                continue
            found = self._stall_walk(holder)
            if found is None:
                continue
            signature, edges = found
            if confirm and self._stall_last.get(holder) != signature:
                seen[holder] = signature
                continue
            self.stalls[holder] = self._stall_report(holder, edges)
            sys.stderr.write("\n" + "\n".join(self.stalls[holder]) + "\n")
            sys.stderr.flush()
        self._stall_last = seen

    def _stall_report(self, holder: str, edges: List[Tuple[str, ...]]) -> List[str]:
        """The report: what is held, then each connection walked back.

        Agents the framework inserted (``broadcast_N``, ``merge_N``) are
        walked through but not named: a reader cannot find them in the
        office file. Each connection is shown from the agent the person
        wrote to the agent the person wrote.
        """
        def inserted(name: str) -> bool:
            return bool(getattr(self.all_agents.get(name), "framework_inserted", False))

        # For an inserted agent, the inbox (written by the person) it feeds.
        target: Dict[str, Tuple[str, str]] = {}
        for to, inbox, frm, _outbox, _state in edges:
            if frm and inserted(frm):
                target[frm] = target.get(to, (to, inbox)) if inserted(to) else (to, inbox)

        info = self.holding[holder]
        lines = [f"Stalled: {holder} holds {info.get('what', 'work')}; it will never arrive."]
        for to, inbox, frm, outbox, state in edges:
            if frm and inserted(frm):
                continue
            shown_to, shown_in = target.get(to, (to, inbox)) if inserted(to) else (to, inbox)
            if not frm:
                lines.append(f"  {shown_to}.{_port(shown_in)}: {state}")
            else:
                lines.append(f"  {shown_to}.{_port(shown_in)} <- {frm}.{_port(outbox)}: "
                             f"empty; {state}")
        # Work queued behind the holder, on inboxes it is not reading.
        for inbox in self.all_agents[holder].inports:
            feed = self._feeds.get((holder, inbox))
            if feed is None or inbox in info.get("needs", []):
                continue
            waiting = self.edge_sent.get(feed, 0) - self.edge_received.get((holder, inbox), 0)
            if waiting > 0:
                lines.append(f"  {waiting} message(s) wait unread on {holder}.{_port(inbox)}.")
        return lines

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

        Delegates to dissyslab.runtime.snapshot.write_snapshot which owns
        the on-disk layout and naming conventions (see that module
        for the full specification).
        """
        if self.snapshot_dir is None:
            return  # in-memory only mode
        from dissyslab.runtime.snapshot import write_snapshot
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


def _port(name: str) -> str:
    """A runtime port name as the office file writes it (``in_`` is ``in``)."""
    return name[:-1] if name in ("in_", "out_") else name
