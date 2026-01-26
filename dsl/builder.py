# dsl/builder.py
"""
User-facing API for building networks.

This module provides:
- PortReference: Enable dot notation for explicit port specification
- network(): Main entry point for creating networks from edge lists
"""

from __future__ import annotations
from typing import List, Tuple, Union, Dict, TYPE_CHECKING

if TYPE_CHECKING:
    from dsl.core import Agent

# Actual imports
from dsl.network import Network


# ============================================================================
# PortReference Class
# ============================================================================

class PortReference:
    """
    Reference to a specific port on an agent.

    Created automatically when accessing agent.port_name via __getattr__.
    Used in network() edges to specify explicit ports.

    Example:
        >>> source.out_
        PortReference(agent=source, port_name="out_")

        >>> network([(source.out_, transform.in_)])
        # Uses PortReference to specify exact ports

    Attributes:
        agent: The agent this port belongs to
        port_name: Name of the port (e.g., "out_", "in_", "out_0")
    """

    def __init__(self, agent: 'Agent', port_name: str):
        """
        Initialize PortReference.

        Args:
            agent: Agent instance that owns this port
            port_name: Name of the port on the agent

        Note:
            Usually created automatically via agent.__getattr__,
            not instantiated directly by users.
        """
        self.agent = agent
        self.port_name = port_name

    def __repr__(self) -> str:
        """
        Readable representation for debugging.

        Returns:
            String like "PortReference(agent_name.port_name)"
        """
        agent_name = self.agent.name if self.agent.name else "<unnamed>"
        return f"PortReference({agent_name}.{self.port_name})"

    def __str__(self) -> str:
        """
        String representation using dot notation.

        Returns:
            String like "agent_name.port_name"
        """
        agent_name = self.agent.name if self.agent.name else "<unnamed>"
        return f"{agent_name}.{self.port_name}"


# ============================================================================
# Helper Functions
# ============================================================================

def _parse_from_node(node: Union['Agent', PortReference], edge_index: int) -> Tuple['Agent', str]:
    """
    Parse from-node of an edge.

    Args:
        node: Agent or PortReference
        edge_index: Index of edge (for error messages)

    Returns:
        (agent, port_name) tuple

    Raises:
        TypeError: If node is not Agent or PortReference
        ValueError: If Agent has no default outport
        ValueError: If port doesn't exist on agent
    """
    from dsl.core import Agent

    # Case 1: PortReference (explicit port)
    if isinstance(node, PortReference):
        agent = node.agent
        port = node.port_name

        # Validate port exists
        if port not in agent.outports:
            raise ValueError(
                f"Edge {edge_index}: Port '{port}' is not a valid outport of agent '{agent.name}'.\n"
                f"Valid outports: {agent.outports}\n\n"
                f"Did you mean one of these?\n" +
                "\n".join(f"  {agent.name}.{p}" for p in agent.outports)
            )

        return agent, port

    # Case 2: Agent (use default port)
    elif isinstance(node, Agent):
        agent = node
        port = agent.default_outport

        if port is None:
            raise ValueError(
                f"Edge {edge_index}: Agent '{agent.name}' has no default outport.\n"
                f"The agent has these outports: {agent.outports}\n\n"
                f"Use explicit port syntax:\n" +
                "\n".join(f"  ({agent.name}.{p}, ...)" for p in agent.outports) +
                f"\n\nExample:\n"
                f"  ({agent.name}.{agent.outports[0] if agent.outports else 'port_name'}, next_agent)"
            )

        return agent, port

    # Case 3: Invalid type
    else:
        raise TypeError(
            f"Edge {edge_index}: from-node must be Agent or PortReference, "
            f"got {type(node).__name__}\n\n"
            f"Expected:\n"
            f"  (agent, ...)              # Agent instance\n"
            f"  (agent.port_name, ...)    # PortReference\n\n"
            f"Got: {node}"
        )


def _parse_to_node(node: Union['Agent', PortReference], edge_index: int) -> Tuple['Agent', str]:
    """
    Parse to-node of an edge.

    Args:
        node: Agent or PortReference
        edge_index: Index of edge (for error messages)

    Returns:
        (agent, port_name) tuple

    Raises:
        TypeError: If node is not Agent or PortReference
        ValueError: If Agent has no default inport
        ValueError: If port doesn't exist on agent
    """
    from dsl.core import Agent

    # Case 1: PortReference (explicit port)
    if isinstance(node, PortReference):
        agent = node.agent
        port = node.port_name

        # Validate port exists
        if port not in agent.inports:
            raise ValueError(
                f"Edge {edge_index}: Port '{port}' is not a valid inport of agent '{agent.name}'.\n"
                f"Valid inports: {agent.inports}\n\n"
                f"Did you mean one of these?\n" +
                "\n".join(f"  {agent.name}.{p}" for p in agent.inports)
            )

        return agent, port

    # Case 2: Agent (use default port)
    elif isinstance(node, Agent):
        agent = node
        port = agent.default_inport

        if port is None:
            raise ValueError(
                f"Edge {edge_index}: Agent '{agent.name}' has no default inport.\n"
                f"The agent has these inports: {agent.inports}\n\n"
                f"Use explicit port syntax:\n" +
                "\n".join(f"  (..., {agent.name}.{p})" for p in agent.inports) +
                f"\n\nExample:\n"
                f"  (prev_agent, {agent.name}.{agent.inports[0] if agent.inports else 'port_name'})"
            )

        return agent, port

    # Case 3: Invalid type
    else:
        raise TypeError(
            f"Edge {edge_index}: to-node must be Agent or PortReference, "
            f"got {type(node).__name__}\n\n"
            f"Expected:\n"
            f"  (..., agent)              # Agent instance\n"
            f"  (..., agent.port_name)    # PortReference\n\n"
            f"Got: {node}"
        )


def _add_agent_to_blocks(blocks: Dict[str, 'Agent'], agent: 'Agent') -> None:
    """
    Add agent to blocks dictionary with duplicate checking.

    Args:
        blocks: Dictionary mapping names to agents
        agent: Agent to add

    Raises:
        ValueError: If agent name already exists with different instance
    """
    if agent.name not in blocks:
        blocks[agent.name] = agent
    elif blocks[agent.name] is not agent:
        raise ValueError(
            f"Duplicate agent name: '{agent.name}'\n\n"
            f"Two different agent instances have the same name.\n"
            f"Each agent must have a unique name.\n\n"
            f"Solution: Give agents different names:\n"
            f"  source_a = Source(fn=gen_a, name='src_a')\n"
            f"  source_b = Source(fn=gen_b, name='src_b')\n"
        )


# ============================================================================
# Main network() Function
# ============================================================================

def network(
    edges: List[Tuple[Union['Agent', PortReference],
                      Union['Agent', PortReference]]]
) -> Network:
    """
    Build a Network from edge list.

    Each edge is a 2-tuple connecting two nodes. Nodes can be:
    - Agent instance: Uses agent's default port
    - PortReference: Uses explicit port (agent.port_name)

    Four edge patterns:
    1. (agent, agent): Both use default ports
    2. (agent.port, agent): Explicit from, default to
    3. (agent, agent.port): Default from, explicit to
    4. (agent.port, agent.port): Both explicit

    Args:
        edges: List of 2-tuples (from_node, to_node)

    Returns:
        Network instance ready to compile and run

    Raises:
        TypeError: If edges is not a list
        TypeError: If edge is not a 2-tuple
        TypeError: If edge nodes are not Agent or PortReference
        ValueError: If agent has no default port when needed
        ValueError: If agent names are not unique
        ValueError: If port doesn't exist on agent

    Example:
        >>> source = Source(fn=generate, name="src")
        >>> transform = Transform(fn=process, name="trans")
        >>> sink = Sink(fn=save, name="sink")
        >>> 
        >>> g = network([
        ...     (source, transform),
        ...     (transform, sink)
        ... ])
        >>> g.run_network()
    """
    # Step 1: Validate input type
    if not isinstance(edges, list):
        raise TypeError(
            f"edges must be a list, got {type(edges).__name__}\n\n"
            f"Example:\n"
            f"  g = network([\n"
            f"      (source, transform),\n"
            f"      (transform, sink)\n"
            f"  ])"
        )

    # Step 2: Parse edges and collect agents
    blocks: Dict[str, 'Agent'] = {}
    connections: List[Tuple[str, str, str, str]] = []

    for i, edge in enumerate(edges):
        # Validate edge structure
        if not isinstance(edge, tuple) or len(edge) != 2:
            edge_type = type(edge).__name__
            edge_len = len(edge) if isinstance(edge, tuple) else "N/A"
            raise TypeError(
                f"Edge {i} must be a 2-tuple, got {edge_type} with {edge_len} elements\n\n"
                f"Expected format:\n"
                f"  (source, transform)              # Both agents\n"
                f"  (source.out_, transform.in_)     # Both PortReferences\n"
                f"  (source.out_, transform)         # Mixed\n\n"
                f"Got: {edge}"
            )

        from_node, to_node = edge

        # Parse from side
        from_agent, from_port = _parse_from_node(from_node, i)

        # Parse to side
        to_agent, to_port = _parse_to_node(to_node, i)

        # Add agents to blocks dict (check for duplicates)
        _add_agent_to_blocks(blocks, from_agent)
        _add_agent_to_blocks(blocks, to_agent)

        # Create 4-tuple connection
        connections.append((
            from_agent.name,
            from_port,
            to_agent.name,
            to_port
        ))

    # Step 3: Create and return Network
    return Network(blocks=blocks, connections=connections)
