# dsl/composed_agent.py
"""
composed_agent: A reusable network component with a named interface.

ComposedAgent is a subclass of Network with:
- Declared inports and outports (the interface)
- Dot notation for port references: pipeline.input, pipeline.output
- A .network setter that wires the implementation

Usage:

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

from __future__ import annotations
from typing import List, Optional
from dissyslab.network import Network


class ComposedAgent(Network):
    """
    A named Network with declared external ports and dot-notation access.

    Subclasses Network so _flatten_networks() handles it automatically.
    Adds __getattr__ for port dot-notation (pipeline.input → PortReference).
    """

    def __init__(self, *, name: str, inputs: List[str], outputs: List[str]):
        if not isinstance(name, str) or not name:
            raise ValueError(
                "composed_agent requires a non-empty string name.")
        if not isinstance(inputs, list) or not all(isinstance(p, str) for p in inputs):
            raise TypeError("inputs must be a list of strings.")
        if not isinstance(outputs, list) or not all(isinstance(p, str) for p in outputs):
            raise TypeError("outputs must be a list of strings.")

        # Initialise as a minimal Network shell — no blocks or connections yet.
        # We bypass Network.__init__ validation by setting attributes directly,
        # then call check() only after .network is assigned.
        self.name = name
        self.inports = list(inputs)
        self.outports = list(outputs)
        self.blocks = {}
        self.connections = []

        # Compilation state (mirrors Network)
        self.compiled = False
        self.agents = {}
        self.graph_connections = []
        self.queues = []
        self.threads = []
        self.unresolved_connections = []

    # ── Port dot-notation ────────────────────────────────────────────────────

    def __getattr__(self, name: str):
        """
        Return a PortReference for any declared input or output port name.

            pipeline.input   → PortReference(pipeline, "input")
            pipeline.output  → PortReference(pipeline, "output")
        """
        from dissyslab.builder import PortReference

        inports = object.__getattribute__(self, 'inports')
        outports = object.__getattribute__(self, 'outports')

        if name in inports or name in outports:
            return PortReference(agent=self, port_name=name)

        raise AttributeError(
            f"'{object.__getattribute__(self, 'name')}' has no port '{name}'.\n"
            f"Declared inputs:  {inports}\n"
            f"Declared outputs: {outports}"
        )

    # ── .network assignment ──────────────────────────────────────────────────

    @property
    def network(self) -> Optional[List]:
        """Returns the edge list (for inspection), or None if not yet wired."""
        return self._edges if hasattr(self, '_edges') else None

    @network.setter
    def network(self, edges: list) -> None:
        """
        Wire the implementation from an edge list.

        Edges use the same syntax as network() in builder.py.
        BoundaryPort is not needed — use dot notation on self:

            (pipeline.input,  transform_1)     # PortReference → agent
            (transform_1,     transform_2)     # agent → agent
            (transform_2,     pipeline.output) # agent → PortReference
        """
        from dissyslab.builder import PortReference, _parse_from_node, _parse_to_node, _add_agent_to_blocks

        if not isinstance(edges, list):
            raise TypeError(
                f"composed_agent.network must be a list of edges, "
                f"got {type(edges).__name__}"
            )

        self._edges = edges
        blocks = {}
        connections = []

        for i, edge in enumerate(edges):
            if not isinstance(edge, tuple) or len(edge) != 2:
                raise TypeError(
                    f"Edge {i} must be a 2-tuple, got {type(edge).__name__}")

            from_node, to_node = edge

            # PortReference pointing to self = boundary port
            from_is_boundary = (isinstance(from_node, PortReference) and
                                from_node.agent is self)
            to_is_boundary = (isinstance(to_node, PortReference) and
                              to_node.agent is self)

            if from_is_boundary and to_is_boundary:
                raise ValueError(f"Edge {i}: both sides are boundary ports.")

            if from_is_boundary:
                # external input → inner block
                port = from_node.port_name
                if port not in self.inports:
                    raise ValueError(
                        f"Edge {i}: '{port}' is not a declared input.")
                to_obj, to_port = _parse_to_node(to_node, i)
                _add_agent_to_blocks(blocks, to_obj)
                connections.append(("external", port, to_obj.name, to_port))

            elif to_is_boundary:
                # inner block → external output
                port = to_node.port_name
                if port not in self.outports:
                    raise ValueError(
                        f"Edge {i}: '{port}' is not a declared output.")
                from_obj, from_port = _parse_from_node(from_node, i)
                _add_agent_to_blocks(blocks, from_obj)
                connections.append(
                    (from_obj.name, from_port, "external", port))

            else:
                # regular inner edge
                from_obj, from_port = _parse_from_node(from_node, i)
                to_obj,   to_port = _parse_to_node(to_node, i)
                _add_agent_to_blocks(blocks, from_obj)
                _add_agent_to_blocks(blocks, to_obj)
                connections.append(
                    (from_obj.name, from_port, to_obj.name, to_port))

        # Install blocks and connections into self, then validate
        self.blocks = blocks
        self.connections = connections
        self.check()   # Network.check() validates structure

    def __repr__(self) -> str:
        status = "wired" if self.blocks else "interface only"
        return (f"ComposedAgent(name={self.name!r}, "
                f"inputs={self.inports}, outputs={self.outports}, {status})")


# ============================================================================
# Public factory
# ============================================================================

def composed_agent(*, name: str, inputs: List[str], outputs: List[str]) -> ComposedAgent:
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
