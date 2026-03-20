# dsl/composed_agent.py
"""
composed_agent: Define a reusable network component with a named interface.

A composed_agent has a fixed interface (inputs and outputs) and an
interchangeable implementation (.network). The interface and implementation
are specified separately — swap implementations without touching the outer network.

Usage:

    # Step 1 — Declare the interface
    pipeline = composed_agent(
        name="pipeline",
        inputs=["input"],
        outputs=["output"],
    )

    # Step 2 — Wire the implementation using agent objects and dot notation
    pipeline.network = [
        (pipeline.input,   transform_1),
        (transform_1,      transform_2),
        (transform_2,      pipeline.output),
    ]

    # Step 3 — Use in an outer network exactly like any other agent
    g = network([
        (source,           pipeline.input),
        (pipeline.output,  sink),
    ])
    g.run_network()

The outer network sees pipeline as a black box with named ports.
Swap the implementation in Step 2 — Step 3 is unchanged.
"""

from __future__ import annotations
from typing import List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from dsl.network import Network


# ============================================================================
# BoundaryPort
# ============================================================================

class BoundaryPort:
    """
    Sentinel representing an external port on a composed_agent.

    Returned by composed_agent.port_name dot notation.
    Used in .network edges and outer network() edges exactly like
    PortReference on regular agents.

    In .network edges:  signals "connect to external port"
    In outer edges:     signals "this is the composed agent's port"
    """

    def __init__(self, owner: 'ComposedAgent', port_name: str, direction: str):
        """
        Args:
            owner:      The ComposedAgent this port belongs to
            port_name:  The declared port name (e.g. "claims")
            direction:  "in" for inputs, "out" for outputs
        """
        self.owner = owner
        self.port_name = port_name
        self.direction = direction

    def __repr__(self) -> str:
        return f"BoundaryPort({self.owner.name}.{self.port_name})"


# ============================================================================
# ComposedAgent
# ============================================================================

class ComposedAgent:
    """
    A named network component with a declared interface and swappable implementation.

    After .network is assigned, delegates structural attributes to the inner
    Network so it is transparent to Network.check() and _flatten_networks().
    """

    def __init__(self, *, name: str, inputs: List[str], outputs: List[str]):
        if not isinstance(name, str) or not name:
            raise ValueError(
                "composed_agent requires a non-empty string name.")
        if not isinstance(inputs, list) or not all(isinstance(p, str) for p in inputs):
            raise TypeError("inputs must be a list of strings.")
        if not isinstance(outputs, list) or not all(isinstance(p, str) for p in outputs):
            raise TypeError("outputs must be a list of strings.")

        # Store in __dict__ directly to avoid __getattr__ recursion
        object.__setattr__(self, 'name',        name)
        object.__setattr__(self, 'inports',     list(inputs))
        object.__setattr__(self, 'outports',    list(outputs))
        object.__setattr__(self, '_input_set',  set(inputs))
        object.__setattr__(self, '_output_set', set(outputs))
        # Network, set by .network
        object.__setattr__(self, '_inner',      None)

    # ── Port dot-notation ────────────────────────────────────────────────────

    def __getattr__(self, name: str) -> BoundaryPort:
        """
        Return a BoundaryPort for any declared input or output port name.

            pipeline.input   → BoundaryPort (direction="in")
            pipeline.output  → BoundaryPort (direction="out")
        """
        input_set = object.__getattribute__(self, '_input_set')
        output_set = object.__getattribute__(self, '_output_set')

        if name in input_set:
            return BoundaryPort(self, name, "in")
        if name in output_set:
            return BoundaryPort(self, name, "out")

        raise AttributeError(
            f"'{object.__getattribute__(self, 'name')}' has no port '{name}'.\n"
            f"Declared inputs:  {object.__getattribute__(self, 'inports')}\n"
            f"Declared outputs: {object.__getattribute__(self, 'outports')}"
        )

    # ── .network assignment ──────────────────────────────────────────────────

    @property
    def network(self) -> Optional['Network']:
        return object.__getattribute__(self, '_inner')

    @network.setter
    def network(self, edges: list) -> None:
        """
        Wire the inner implementation from an edge list.

        Edges follow the same object/dot-notation conventions as network()
        in builder.py, plus BoundaryPort sentinels for boundary connections:

            (pipeline.input,   transform_1)    # external input → inner agent
            (transform_1,      transform_2)    # inner agent    → inner agent
            (transform_2,      pipeline.output) # inner agent   → external output
        """
        from dsl.network import Network
        from dsl.builder import _parse_from_node, _parse_to_node, _add_agent_to_blocks

        if not isinstance(edges, list):
            raise TypeError(
                f"composed_agent.network must be a list of edges, "
                f"got {type(edges).__name__}"
            )

        inports = object.__getattribute__(self, 'inports')
        outports = object.__getattribute__(self, 'outports')
        name = object.__getattribute__(self, 'name')

        blocks = {}
        connections = []

        for i, edge in enumerate(edges):
            if not isinstance(edge, tuple) or len(edge) != 2:
                raise TypeError(
                    f"Edge {i} must be a 2-tuple, got {type(edge).__name__}"
                )

            from_node, to_node = edge

            from_is_boundary = isinstance(from_node, BoundaryPort)
            to_is_boundary = isinstance(to_node,   BoundaryPort)

            if from_is_boundary and to_is_boundary:
                raise ValueError(
                    f"Edge {i}: both sides are boundary ports. "
                    f"At least one side must be an inner agent."
                )

            if from_is_boundary:
                # External input → inner agent
                bp = from_node
                if bp.direction != "in":
                    raise ValueError(
                        f"Edge {i}: '{bp.port_name}' is an output port "
                        f"and cannot be the source of an edge."
                    )
                to_agent, to_port = _parse_to_node(to_node, i)
                _add_agent_to_blocks(blocks, to_agent)
                connections.append(
                    ("external", bp.port_name, to_agent.name, to_port))

            elif to_is_boundary:
                # Inner agent → external output
                bp = to_node
                if bp.direction != "out":
                    raise ValueError(
                        f"Edge {i}: '{bp.port_name}' is an input port "
                        f"and cannot be the destination of an edge."
                    )
                from_agent, from_port = _parse_from_node(from_node, i)
                _add_agent_to_blocks(blocks, from_agent)
                connections.append(
                    (from_agent.name, from_port, "external", bp.port_name))

            else:
                # Regular inner edge — both sides are agents / PortReferences
                from_agent, from_port = _parse_from_node(from_node, i)
                to_agent,   to_port = _parse_to_node(to_node, i)
                _add_agent_to_blocks(blocks, from_agent)
                _add_agent_to_blocks(blocks, to_agent)
                connections.append(
                    (from_agent.name, from_port, to_agent.name, to_port))

        inner = Network(
            name=name,
            blocks=blocks,
            connections=connections,
            inports=inports,
            outports=outports,
        )
        object.__setattr__(self, '_inner', inner)

    # ── Delegate structural attributes to inner Network ──────────────────────
    # Network.check() tests isinstance(block, (Agent, Network)).
    # We handle this in builder.py's _parse_from_node/_parse_to_node by
    # detecting BoundaryPort and extracting the inner Network directly.
    # The delegation here covers the case where ComposedAgent ends up
    # in a blocks dict (it shouldn't, but guards against it).

    def __getattribute__(self, name: str):
        # Always serve our own core attributes directly
        if name in ('name', 'inports', 'outports', 'network',
                    '_inner', '_input_set', '_output_set',
                    '__class__', '__dict__', '__repr__', '__getattr__'):
            return object.__getattribute__(self, name)

        # After .network is set, delegate Network structural attributes
        inner = object.__getattribute__(self, '_inner')
        if inner is not None and name in (
            'blocks', 'connections', 'check',
            'compile', 'compiled',
            'agents', 'graph_connections',
            'queues', 'threads', 'unresolved_connections',
        ):
            return getattr(inner, name)

        return object.__getattribute__(self, name)

    def __repr__(self) -> str:
        name = object.__getattribute__(self, 'name')
        ins = object.__getattribute__(self, 'inports')
        outs = object.__getattribute__(self, 'outports')
        inner = object.__getattribute__(self, '_inner')
        status = "wired" if inner else "interface only"
        return f"ComposedAgent(name={name!r}, inputs={ins}, outputs={outs}, {status})"


# ============================================================================
# Public factory function
# ============================================================================

def composed_agent(
    *,
    name: str,
    inputs: List[str],
    outputs: List[str],
) -> ComposedAgent:
    """
    Declare a named network component with a fixed interface.

    Args:
        name:    Unique name for this component
        inputs:  List of named input port names
        outputs: List of named output port names

    Returns:
        ComposedAgent. Assign .network to wire the implementation.

    Example:
        pipeline = composed_agent(
            name="pipeline",
            inputs=["input"],
            outputs=["output"],
        )
        pipeline.network = [
            (pipeline.input,  transform_1),
            (transform_1,     transform_2),
            (transform_2,     pipeline.output),
        ]
        g = network([
            (source,           pipeline.input),
            (pipeline.output,  sink),
        ])
        g.run_network()
    """
    return ComposedAgent(name=name, inputs=inputs, outputs=outputs)
