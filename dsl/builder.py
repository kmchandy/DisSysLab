# dsl/builder.py
from __future__ import annotations
from typing import List, Tuple, Union, Dict, TYPE_CHECKING

if TYPE_CHECKING:
    from dsl.core import Agent

from dsl.network import Network


class PortReference:
    def __init__(self, agent, port_name):
        self.agent = agent
        self.port_name = port_name

    def __repr__(self):
        return f"PortReference({self.agent.name}.{self.port_name})"

    def __str__(self):
        return f"{self.agent.name}.{self.port_name}"


def _build_registry(edges):
    from dsl.core import Agent
    registry = {}
    for edge in edges:
        for node in edge:
            agent = None
            if isinstance(node, Agent):
                agent = node
            elif isinstance(node, PortReference):
                agent = node.agent
            if agent is not None:
                if agent.name in registry and registry[agent.name] is not agent:
                    raise ValueError(f"Duplicate agent name: '{agent.name}'")
                registry[agent.name] = agent
    return registry


def _resolve_status_to_port(agent, status, edge_index):
    try:
        from dsl.blocks.role import Role
        if isinstance(agent, Role):
            if status not in agent._status_to_port:
                raise ValueError(
                    f"Edge {edge_index}: Agent '{agent.name}' has no status '{status}'.")
            return agent._status_to_port[status]
    except ImportError:
        pass
    if status != "all":
        raise ValueError(
            f"Edge {edge_index}: Only Role agents support named statuses. Use 'all'.")
    if len(agent.outports) != 1:
        raise ValueError(
            f"Edge {edge_index}: Agent '{agent.name}' needs explicit port.")
    return agent.outports[0]


def _preprocess_edges(edges):
    from dsl.core import Agent
    registry = _build_registry(edges)
    processed = []
    for i, edge in enumerate(edges):
        if (isinstance(edge, tuple) and len(edge) == 3 and
                all(isinstance(e, str) for e in edge)):
            sender_name, status, receiver_name = edge
            if sender_name not in registry:
                raise ValueError(f"Edge {i}: Unknown agent '{sender_name}'.")
            if receiver_name not in registry:
                raise ValueError(f"Edge {i}: Unknown agent '{receiver_name}'.")
            sender = registry[sender_name]
            receiver = registry[receiver_name]
            outport = _resolve_status_to_port(sender, status, i)
            processed.append(
                (PortReference(agent=sender, port_name=outport), receiver))
        else:
            processed.append(edge)
    return processed


def _parse_from_node(node, edge_index):
    from dsl.core import Agent
    from dsl.composed_agent import BoundaryPort

    if isinstance(node, BoundaryPort):
        # BoundaryPort on left = composed_agent's output port
        if node.direction != "out":
            raise ValueError(
                f"Edge {edge_index}: '{node.port_name}' is an input port "
                f"and cannot be the source of an edge."
            )
        inner = object.__getattribute__(node.owner, '_inner')
        if inner is None:
            raise ValueError(
                f"Edge {edge_index}: ComposedAgent '{node.owner.name}' has no "
                f".network assigned yet."
            )
        return inner, node.port_name

    elif isinstance(node, PortReference):
        agent = node.agent
        port = node.port_name
        if port not in agent.outports:
            raise ValueError(
                f"Edge {edge_index}: '{port}' is not a valid outport of '{agent.name}'. "
                f"Valid: {agent.outports}"
            )
        return agent, port

    elif isinstance(node, Agent):
        port = node.default_outport
        if port is None:
            raise ValueError(
                f"Edge {edge_index}: Agent '{node.name}' has no default outport."
            )
        return node, port

    else:
        raise TypeError(
            f"Edge {edge_index}: from-node must be Agent, PortReference, or BoundaryPort, "
            f"got {type(node).__name__}"
        )


def _parse_to_node(node, edge_index):
    from dsl.core import Agent
    from dsl.composed_agent import BoundaryPort

    if isinstance(node, BoundaryPort):
        # BoundaryPort on right = composed_agent's input port
        if node.direction != "in":
            raise ValueError(
                f"Edge {edge_index}: '{node.port_name}' is an output port "
                f"and cannot be the destination of an edge."
            )
        inner = object.__getattribute__(node.owner, '_inner')
        if inner is None:
            raise ValueError(
                f"Edge {edge_index}: ComposedAgent '{node.owner.name}' has no "
                f".network assigned yet."
            )
        return inner, node.port_name

    elif isinstance(node, PortReference):
        agent = node.agent
        port = node.port_name
        if port not in agent.inports:
            raise ValueError(
                f"Edge {edge_index}: '{port}' is not a valid inport of '{agent.name}'. "
                f"Valid: {agent.inports}"
            )
        return agent, port

    elif isinstance(node, Agent):
        port = node.default_inport
        if port is None:
            raise ValueError(
                f"Edge {edge_index}: Agent '{node.name}' has no default inport."
            )
        return node, port

    else:
        raise TypeError(
            f"Edge {edge_index}: to-node must be Agent, PortReference, or BoundaryPort, "
            f"got {type(node).__name__}"
        )


def _add_agent_to_blocks(blocks, obj):
    """Accept Agent or Network (for ComposedAgent inner networks)."""
    if obj.name not in blocks:
        blocks[obj.name] = obj
    elif blocks[obj.name] is not obj:
        raise ValueError(f"Duplicate name: '{obj.name}'")


def network(edges):
    if not isinstance(edges, list):
        raise TypeError(f"edges must be a list, got {type(edges).__name__}")

    edges = _preprocess_edges(edges)

    blocks = {}
    connections = []

    for i, edge in enumerate(edges):
        if not isinstance(edge, tuple) or len(edge) != 2:
            raise TypeError(f"Edge {i} must be a 2-tuple")

        from_node, to_node = edge
        from_obj, from_port = _parse_from_node(from_node, i)
        to_obj,   to_port = _parse_to_node(to_node, i)

        _add_agent_to_blocks(blocks, from_obj)
        _add_agent_to_blocks(blocks, to_obj)

        connections.append((from_obj.name, from_port, to_obj.name, to_port))

    return Network(blocks=blocks, connections=connections)
