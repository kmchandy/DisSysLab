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
                f"Use explicit port syntax: ({agent.name}.port_name, ...)"
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
    edges: List[Tuple[Union['Agent', PortReference],
                      Union['Agent', PortReference]]]
) -> Network:
    """
    Build a Network from edge list.

    Args:
        edges: List of 2-tuples (from_node, to_node)

    Returns:
        Network instance ready to compile and run
    """
    if not isinstance(edges, list):
        raise TypeError(
            f"edges must be a list, got {type(edges).__name__}"
        )

    blocks: Dict[str, 'Agent'] = {}
    connections: List[Tuple[str, str, str, str]] = []

    for i, edge in enumerate(edges):
        if not isinstance(edge, tuple) or len(edge) != 2:
            raise TypeError(
                f"Edge {i} must be a 2-tuple, got {type(edge).__name__}"
            )

        from_node, to_node = edge

        # Parse from side
        from_agent, from_port = _parse_from_node(from_node, i)

        # Parse to side
        to_agent, to_port = _parse_to_node(to_node, i)

        # Add agents to blocks dict
        _add_agent_to_blocks(blocks, from_agent)
        _add_agent_to_blocks(blocks, to_agent)

        # Create 4-tuple connection
        connections.append((
            from_agent.name,
            from_port,
            to_agent.name,
            to_port
        ))

    return Network(blocks=blocks, connections=connections)
