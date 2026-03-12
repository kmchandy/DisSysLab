# dsl/builder.py
"""
User-facing API for building networks.

This module provides:
- PortReference: Enable dot notation for explicit port specification
- network(): Main entry point for creating networks from edge lists

Edges can be specified in three ways:

    # 1. Agent objects (existing syntax):
    (source, transform)

    # 2. Explicit port references (existing syntax):
    (editor.out_0, sink)

    # 3. String triples with status (new org syntax):
    ("editor", "interesting", "jsonl_recorder")
    ("editor", "all",         "copy_writer")

The string triple syntax is converted to object-based edges before
any existing validation or compilation code runs. Zero changes to
network.py or downstream infrastructure.
"""

from __future__ import annotations
from typing import List, Tuple, Union, Dict, TYPE_CHECKING

if TYPE_CHECKING:
    from dsl.core import Agent

from dsl.network import Network


# ============================================================================
# PortReference Class
# ============================================================================

class PortReference:
    """
    Reference to a specific port on an agent.

    Created automatically when accessing agent.port_name via __getattr__.
    Used in network() edges to specify explicit ports.
    """

    def __init__(self, agent: 'Agent', port_name: str):
        self.agent = agent
        self.port_name = port_name

    def __repr__(self) -> str:
        agent_name = self.agent.name if self.agent.name else "<unnamed>"
        return f"PortReference({agent_name}.{self.port_name})"

    def __str__(self) -> str:
        agent_name = self.agent.name if self.agent.name else "<unnamed>"
        return f"{agent_name}.{self.port_name}"


# ============================================================================
# String Edge Preprocessing
# ============================================================================

def _build_registry(edges: list) -> Dict[str, 'Agent']:
    """
    Build a name→agent registry by scanning all edges for agent objects.

    Collects every Agent and PortReference.agent found anywhere in the
    edge list. String edges are skipped — they are resolved using this
    registry after it is built.

    Args:
        edges: Raw edge list as passed to network()

    Returns:
        Dict mapping agent.name → agent for every agent found in edges

    Raises:
        ValueError: If two different agents share the same name
    """
    from dsl.core import Agent

    registry: Dict[str, Agent] = {}

    for edge in edges:
        for node in edge:
            agent = None
            if isinstance(node, Agent):
                agent = node
            elif isinstance(node, PortReference):
                agent = node.agent

            if agent is not None:
                if agent.name in registry and registry[agent.name] is not agent:
                    raise ValueError(
                        f"Two different agents share the name '{agent.name}'. "
                        f"Each agent must have a unique name."
                    )
                registry[agent.name] = agent

    return registry


def _resolve_status_to_port(agent: 'Agent', status: str, edge_index: int) -> str:
    """
    Resolve a status string to an outport name for the given agent.

    For Role agents: uses _status_to_port mapping.
    For all others: "all" maps to the agent's single outport.

    Args:
        agent: The sending agent
        status: Status string from the edge triple
        edge_index: Index of edge in list (for error messages)

    Returns:
        Outport name (e.g. "out_0", "out_")

    Raises:
        ValueError: If status cannot be resolved
    """
    from dsl.blocks.role import Role

    if isinstance(agent, Role):
        if status not in agent._status_to_port:
            raise ValueError(
                f"Edge {edge_index}: Agent '{agent.name}' has no status '{status}'.\n"
                f"Declared statuses: {agent.statuses}\n"
                f"Use one of: {list(agent._status_to_port.keys())}"
            )
        return agent._status_to_port[status]

    # Non-Role agent: "all" means use the single outport
    if status != "all":
        raise ValueError(
            f"Edge {edge_index}: Agent '{agent.name}' is not a Role agent.\n"
            f"Only Role agents support named statuses.\n"
            f"Use status 'all' for non-Role agents, or use object syntax: "
            f"({agent.name}, receiver)"
        )

    if len(agent.outports) == 0:
        raise ValueError(
            f"Edge {edge_index}: Agent '{agent.name}' has no outports."
        )

    if len(agent.outports) > 1:
        raise ValueError(
            f"Edge {edge_index}: Agent '{agent.name}' has multiple outports {agent.outports}.\n"
            f"Use explicit port syntax: ({agent.name}.port_name, receiver)"
        )

    return agent.outports[0]


def _preprocess_edges(edges: list) -> list:
    """
    Convert string triple edges to object-based edges.

    Scans the edge list for string triples of the form:
        ("sender_name", "status", "receiver_name")

    Resolves each to a 2-tuple of (PortReference, Agent) using:
    - The name→agent registry built from object edges
    - The status→port mapping on Role agents

    Non-string edges are passed through unchanged.

    Args:
        edges: Raw edge list as passed to network()

    Returns:
        New edge list with all string triples converted to object edges

    Raises:
        ValueError: If a string name cannot be resolved
        TypeError: If an edge has wrong format
    """
    from dsl.core import Agent

    # Build registry from all agent objects in the edge list
    registry = _build_registry(edges)

    processed = []

    for i, edge in enumerate(edges):

        # String triple: ("sender", "status", "receiver")
        if (isinstance(edge, tuple) and
                len(edge) == 3 and
                all(isinstance(e, str) for e in edge)):

            sender_name, status, receiver_name = edge

            # Resolve sender
            if sender_name not in registry:
                raise ValueError(
                    f"Edge {i}: Unknown agent '{sender_name}'.\n"
                    f"Known agents: {sorted(registry.keys())}\n"
                    f"Make sure '{sender_name}' appears as an object "
                    f"in at least one edge."
                )

            # Resolve receiver
            if receiver_name not in registry:
                raise ValueError(
                    f"Edge {i}: Unknown agent '{receiver_name}'.\n"
                    f"Known agents: {sorted(registry.keys())}\n"
                    f"Make sure '{receiver_name}' appears as an object "
                    f"in at least one edge."
                )

            sender = registry[sender_name]
            receiver = registry[receiver_name]

            # Resolve status to outport
            outport = _resolve_status_to_port(sender, status, i)

            # Convert to PortReference → Agent (existing format)
            port_ref = PortReference(agent=sender, port_name=outport)
            processed.append((port_ref, receiver))

        else:
            # Pass through existing format unchanged
            processed.append(edge)

    return processed


# ============================================================================
# Helper Functions
# ============================================================================

def _parse_from_node(node: Union['Agent', PortReference], edge_index: int) -> Tuple['Agent', str]:
    """Parse from-node of an edge."""
    from dsl.core import Agent

    if isinstance(node, PortReference):
        agent = node.agent
        port = node.port_name

        if port not in agent.outports:
            raise ValueError(
                f"Edge {edge_index}: Port '{port}' is not a valid outport of agent '{agent.name}'.\n"
                f"Valid outports: {agent.outports}"
            )

        return agent, port

    elif isinstance(node, Agent):
        agent = node
        port = agent.default_outport

        if port is None:
            raise ValueError(
                f"Edge {edge_index}: Agent '{agent.name}' has no default outport.\n"
                f"Use explicit port syntax: ({agent.name}.port_name, ...) \n"
                f"or status syntax: ('{agent.name}', 'status', 'receiver')"
            )

        return agent, port

    else:
        raise TypeError(
            f"Edge {edge_index}: from-node must be Agent or PortReference, "
            f"got {type(node).__name__}"
        )


def _parse_to_node(node: Union['Agent', PortReference], edge_index: int) -> Tuple['Agent', str]:
    """Parse to-node of an edge."""
    from dsl.core import Agent

    if isinstance(node, PortReference):
        agent = node.agent
        port = node.port_name

        if port not in agent.inports:
            raise ValueError(
                f"Edge {edge_index}: Port '{port}' is not a valid inport of agent '{agent.name}'.\n"
                f"Valid inports: {agent.inports}"
            )

        return agent, port

    elif isinstance(node, Agent):
        agent = node
        port = agent.default_inport

        if port is None:
            raise ValueError(
                f"Edge {edge_index}: Agent '{agent.name}' has no default inport.\n"
                f"Use explicit port syntax: (..., {agent.name}.port_name)"
            )

        return agent, port

    else:
        raise TypeError(
            f"Edge {edge_index}: to-node must be Agent or PortReference, "
            f"got {type(node).__name__}"
        )


def _add_agent_to_blocks(blocks: Dict[str, 'Agent'], agent: 'Agent') -> None:
    """Add agent to blocks dictionary with duplicate checking."""
    if agent.name not in blocks:
        blocks[agent.name] = agent
    elif blocks[agent.name] is not agent:
        raise ValueError(
            f"Duplicate agent name: '{agent.name}'\n"
            f"Each agent must have a unique name."
        )


# ============================================================================
# Main network() Function
# ============================================================================

def network(
    edges: List[Union[
        Tuple[Union['Agent', PortReference], Union['Agent', PortReference]],
        Tuple[str, str, str]
    ]]
) -> Network:
    """
    Build a Network from an edge list.

    Edges can be specified in three ways:

        # Agent objects — uses default ports:
        (source, transform)

        # Explicit port references — uses dot notation:
        (editor.out_0, sink)

        # String triples — org syntax with status-based routing:
        ("editor", "interesting", "jsonl_recorder")
        ("editor", "all",         "copy_writer")

    String triples are converted to object edges before validation.
    All three forms can be mixed freely in the same edge list.

    Args:
        edges: List of 2-tuples (object syntax) or 3-tuples (string syntax)

    Returns:
        Network instance ready to compile and run

    Example — pure org syntax:
        g = network([
            (src_aj,    "all",         editor),
            (src_bbc,   "all",         editor),
            ("editor",  "interesting", "recorder"),
            ("editor",  "boring",      "copy_writer"),
            ("editor",  "exhausted",   "recorder"),
            ("copy_writer", "all",     "editor"),
        ])
    """
    if not isinstance(edges, list):
        raise TypeError(
            f"edges must be a list, got {type(edges).__name__}"
        )

    # Convert string triples to object edges
    edges = _preprocess_edges(edges)

    blocks: Dict[str, 'Agent'] = {}
    connections: List[Tuple[str, str, str, str]] = []

    for i, edge in enumerate(edges):
        if not isinstance(edge, tuple) or len(edge) != 2:
            raise TypeError(
                f"Edge {i} must be a 2-tuple after preprocessing, "
                f"got {type(edge).__name__} of length {len(edge) if isinstance(edge, tuple) else '?'}"
            )

        from_node, to_node = edge

        from_agent, from_port = _parse_from_node(from_node, i)
        to_agent, to_port = _parse_to_node(to_node, i)

        _add_agent_to_blocks(blocks, from_agent)
        _add_agent_to_blocks(blocks, to_agent)

        connections.append((
            from_agent.name,
            from_port,
            to_agent.name,
            to_port
        ))

    return Network(blocks=blocks, connections=connections)
