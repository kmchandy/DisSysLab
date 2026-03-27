# dsl/os_agent.py
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
from typing import Dict, List, Tuple, Any, Set
import time

from dsl.core import _GiveMeCounts, _Shutdown


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

    # ── Main loop ─────────────────────────────────────────────────────────────

    def run(self) -> None:
        """
        Poll non-source agents periodically. Drain any messages that have
        arrived (from sources or non-sources). Declare termination when
        all agents heard from and all edges balanced. Then shut down all
        non-source agents.
        """
        while True:
            time.sleep(self.poll_interval)
            self._send_give_me_counts()
            self._drain_responses()
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
        Updates counts from whatever has arrived — sources or non-sources.
        """
        while True:
            try:
                response = self.in_q.get_nowait()
                self._update_counts(response)
            except Empty:
                break

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
