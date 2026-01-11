# dsl/graph.py
from __future__ import annotations
from typing import Any, Dict, Iterable, List, Optional, Tuple
import warnings
import uuid

from dsl.core import Network, Agent, PortReference
from dsl.blocks.source import Source
from dsl.blocks.sink import Sink
from dsl.blocks.transform import Transform
from dsl.blocks.fanout import Broadcast
from dsl.blocks.fanin import MergeAsynch

# Type alias for edges - can be agents or port references
EdgeNode = Agent | PortReference

# ---------------------------------------------------------
#                  HELPER FUNCTIONS                       |
# ---------------------------------------------------------


def _ensure_uid(obj) -> str:
    """
    Ensure the object has a stable UUID. If not, create and store one.

    Args:
        obj: Any Python object (Agent instance, etc.)

    Returns:
        String representation of the UUID
    """
    if not hasattr(obj, "_dsl_uid"):
        obj._dsl_uid = str(uuid.uuid4())
    return obj._dsl_uid


def _resolve_name(agent: Agent, sep: str = "#", uid_sep: str = "@") -> str:
    """
    Give each agent a globally unique name.

    Agent naming:
        <agent_class_name>@<FULL_UUID>

    Examples:
        Source@f47ac10b-58cc-4372-a567-0e02b2c3d479
        Transform@8b9e3d2a-1f4c-4a5b-9c7d-3e8f1a2b4c5d

    This ensures that:
    - Each agent gets a unique name even if the same agent class is used multiple times
    - Different agent instances are distinguished
    """
    # Get the agent's class name
    class_name = agent.__class__.__name__

    # Get or create stable UUID
    u = _ensure_uid(agent)

    return f"{class_name}{uid_sep}{u}"


def _parse_edge_from_node(node: EdgeNode) -> Tuple[Agent, str]:
    """
    Parse the FROM side of an edge (sender).

    Args:
        node: Either an Agent or a PortReference

    Returns:
        Tuple of (agent, output_port_name)

    Raises:
        ValueError: If agent cannot be used as sender
        TypeError: If node is not Agent or PortReference

    Examples:
        >>> source = Source(fn=data.run)
        >>> _parse_edge_from_node(source)
        (source, "out")

        >>> split = Split(router=router, num_outputs=3)
        >>> _parse_edge_from_node(split.out_0)
        (split, "out_0")
    """
    if isinstance(node, PortReference):
        # Explicit port reference: split.out_0
        return node.agent, node.port_name

    elif isinstance(node, Agent):
        # Determine default output port based on agent type
        if isinstance(node, Source):
            return node, "out"
        elif isinstance(node, (Transform, Broadcast)):
            return node, "out"
        elif isinstance(node, Sink):
            raise ValueError(
                f"Sink cannot be used as sender (from side of edge). "
                f"Sinks have no output ports."
            )
        else:
            # Generic agent with unknown ports - requires explicit syntax
            raise ValueError(
                f"Cannot determine output port for {node.__class__.__name__}. "
                f"Use explicit port syntax: agent.port_name"
            )
    else:
        raise TypeError(
            f"Edge node must be Agent or PortReference, got {type(node).__name__}"
        )


def _parse_edge_to_node(node: EdgeNode) -> Tuple[Agent, str]:
    """
    Parse the TO side of an edge (receiver).

    Args:
        node: Either an Agent or a PortReference

    Returns:
        Tuple of (agent, input_port_name)

    Raises:
        ValueError: If agent cannot be used as receiver
        TypeError: If node is not Agent or PortReference

    Examples:
        >>> sink = Sink(fn=handler.run)
        >>> _parse_edge_to_node(sink)
        (sink, "in")

        >>> transform = Transform(fn=processor.run)
        >>> _parse_edge_to_node(transform)
        (transform, "in")
    """
    if isinstance(node, PortReference):
        # Explicit port reference: handler.in
        return node.agent, node.port_name

    elif isinstance(node, Agent):
        # Determine default input port based on agent type
        if isinstance(node, Sink):
            return node, "in"
        elif isinstance(node, (Transform, MergeAsynch)):
            return node, "in"
        elif isinstance(node, Source):
            raise ValueError(
                f"Source cannot be used as receiver (to side of edge). "
                f"Sources have no input ports."
            )
        else:
            # Generic agent with unknown ports - requires explicit syntax
            raise ValueError(
                f"Cannot determine input port for {node.__class__.__name__}. "
                f"Use explicit port syntax: agent.port_name"
            )
    else:
        raise TypeError(
            f"Edge node must be Agent or PortReference, got {type(node).__name__}"
        )


# ---------------------------------------------------------
#                  NETWORK BUILDER                        |
# ---------------------------------------------------------


def network(edges: Iterable[Tuple[EdgeNode, EdgeNode]]) -> Graph:
    """
    Build a graph from a list of agent edges.

    Supports both simple and explicit port syntax:

    Simple (Module 1):
        network([
            (source, transform),
            (transform, sink)
        ])

    Explicit (Module 2+):
        network([
            (source, split),
            (split.out_0, handler1),
            (split.out_1, handler2)
        ])

    Args:
        edges: List of (from_node, to_node) tuples where each node is 
               either an Agent or a PortReference (agent.port_name)

    Returns:
        Graph instance ready to compile and run

    Examples:
        >>> # Simple syntax
        >>> g = network([
        ...     (twitter_source, clean),
        ...     (reddit_source, clean),
        ...     (clean, sentiment),
        ...     (sentiment, logger)
        ... ])

        >>> # Explicit ports for Split
        >>> g = network([
        ...     (source, splitter),
        ...     (splitter.out_0, spam_handler),
        ...     (splitter.out_1, safe_handler)
        ... ])
    """

    # Parse edges and build connections
    parsed_edges: List[Tuple[str, str, str, str]] = []
    seen_names: set[str] = set()
    ordered_agents: List[Agent] = []

    for from_node, to_node in edges:
        # Parse from side (sender) - uses context-aware function
        from_agent, from_port = _parse_edge_from_node(from_node)
        from_name = _resolve_name(from_agent)

        # Parse to side (receiver) - uses context-aware function
        to_agent, to_port = _parse_edge_to_node(to_node)
        to_name = _resolve_name(to_agent)

        # Build connection tuple - ports are already determined!
        parsed_edges.append((from_name, from_port, to_name, to_port))

        # Collect unique agents in first-seen order
        for agent, name in ((from_agent, from_name), (to_agent, to_name)):
            if name not in seen_names:
                seen_names.add(name)
                ordered_agents.append(agent)

    # Build node list: (name, agent)
    nodes = [(_resolve_name(agent), agent) for agent in ordered_agents]

    return Graph(edges=parsed_edges, nodes=nodes)


# ---------------------------------------------------------
#                  CLASS GRAPH                           |
# ---------------------------------------------------------


class Graph:
    """
    Graph specification for distributed dataflow networks.

    A Graph:
    - Defines edges as (from_name, from_port, to_name, to_port) tuples
    - Defines nodes as (name, agent) pairs
    - Infers roles (source, transform, sink) from in/out-degree
    - Automatically inserts Broadcast for fanout (>1 outgoing)
    - Automatically inserts Merge for fanin (>1 incoming)
    - Compiles into executable Network with threading and queues

    **Key Changes from Old Version:**
    - Nodes are Agent instances (not functions)
    - No params parameter needed
    - Supports PortReference for explicit port syntax
    - Simplified role inference

    **Examples:**

    Simple pipeline:
        >>> g = Graph(
        ...     edges=[("src", "out", "trans", "in"), 
        ...            ("trans", "out", "snk", "in")],
        ...     nodes=[("src", source_agent), 
        ...            ("trans", transform_agent), 
        ...            ("snk", sink_agent)]
        ... )
        >>> g.run_network()

    With automatic fanout:
        >>> g = Graph(
        ...     edges=[("src", "out", "trans1", "in"),
        ...            ("src", "out", "trans2", "in")],  # Fanout!
        ...     nodes=[("src", source), ("trans1", t1), ("trans2", t2)]
        ... )
        >>> # Broadcast automatically inserted
    """

    def __init__(
        self,
        *,
        edges: Iterable[Tuple[str, str, str, str]],
        nodes: Iterable[Tuple[str, Agent]]
    ) -> None:
        """
        Initialize a Graph.

        Args:
            edges: List of (from_name, from_port, to_name, to_port) tuples
            nodes: List of (name, agent) tuples

        Raises:
            TypeError: If nodes are not Agent instances
            ValueError: If edges reference non-existent nodes or ports
        """
        # Validate and store edges
        edge_list = list(edges)
        for i, e in enumerate(edge_list):
            if not (isinstance(e, (tuple, list)) and len(e) == 4):
                raise TypeError(
                    f"edges[{i}] must be (from_name, from_port, to_name, to_port); got {e!r}"
                )
            fn, fp, tn, tp = e
            if not all(isinstance(x, str) and x.strip() for x in [fn, fp, tn, tp]):
                raise TypeError(
                    f"edges[{i}] all components must be non-empty strings; got {e!r}"
                )

        # Validate and store nodes
        node_list = list(nodes)
        agents_dict: Dict[str, Agent] = {}

        for i, item in enumerate(node_list):
            if not (isinstance(item, (tuple, list)) and len(item) == 2):
                raise TypeError(
                    f"nodes[{i}] must be (name, agent); got {item!r}"
                )
            name, agent = item

            if not (isinstance(name, str) and name.strip()):
                raise TypeError(
                    f"nodes[{i}]: name must be non-empty string; got {name!r}"
                )

            if not isinstance(agent, Agent):
                raise TypeError(
                    f"nodes[{i}]: must be Agent instance; got {type(agent).__name__}"
                )

            if name in agents_dict:
                raise ValueError(
                    f"Duplicate node name '{name}'"
                )

            agents_dict[name] = agent

        self.edges = edge_list
        self._agents = agents_dict
        self.nodes = self._agents.keys()
        self.network: Optional[Network] = None
        self.indeg: Dict[str, int] = {}
        self.outdeg: Dict[str, int] = {}

    def _validate_edges(self) -> None:
        """
        Validate that all edges reference existing nodes and ports.
        """
        # Check that all referenced nodes exist
        referenced = {u for u, _, _, _ in self.edges} | {
            v for _, _, v, _ in self.edges}
        missing = sorted(n for n in referenced if n not in self._agents)

        if missing:
            raise KeyError(
                f"Edge(s) reference non-existent node(s): {missing}\n"
                f"Available nodes: {sorted(self._agents.keys())}"
            )

        # Check that all ports exist on agents
        for (fn, fp, tn, tp) in self.edges:
            from_agent = self._agents[fn]
            to_agent = self._agents[tn]

            if fp not in from_agent.outports:
                raise ValueError(
                    f"Edge references non-existent outport '{fp}' on node '{fn}'\n"
                    f"Available outports: {from_agent.outports}"
                )

            if tp not in to_agent.inports:
                raise ValueError(
                    f"Edge references non-existent inport '{tp}' on node '{tn}'\n"
                    f"Available inports: {to_agent.inports}"
                )

    def _infer_roles(self) -> Dict[str, str]:
        """
        Infer roles from graph topology and insert Broadcast/Merge nodes.

        Automatically detects fanout (out-degree > 1) and fanin (in-degree > 1) 
        patterns and inserts helper agents to maintain the 1-to-1 connection invariant.

        **Fanout:** One agent sending to multiple receivers
            - Detected: node has out-degree > 1
            - Solution: Insert Broadcast agent
            - Broadcast copies each message to all outputs

        **Fanin:** Multiple agents sending to one receiver
            - Detected: node has in-degree > 1
            - Solution: Insert MergeAsynch agent
            - Merge combines multiple streams (first-come-first-served)

        Returns:
            Dictionary mapping node names to roles

        **Complete Example:**

        Student writes:
            >>> g = network([
            ...     (twitter, clean),
            ...     (reddit, clean),      # Fanin at clean
            ...     (clean, sentiment),
            ...     (clean, urgency),     # Fanout from clean
            ...     (sentiment, logger),
            ...     (urgency, logger)     # Fanin at logger
            ... ])

        Initial edges (after parsing):
            [
                ("twitter", "out", "clean", "in"),
                ("reddit", "out", "clean", "in"),    # Same to-port (FANIN)
                ("clean", "out", "sentiment", "in"),
                ("clean", "out", "urgency", "in"),   # Same from-port (FANOUT)
                ("sentiment", "out", "logger", "in"),
                ("urgency", "out", "logger", "in")   # Same to-port (FANIN)
            ]

        Degrees computed:
            indeg = {
                "twitter": 0,
                "reddit": 0,
                "clean": 2,      # ← FANIN detected
                "sentiment": 1,
                "urgency": 1,
                "logger": 2      # ← FANIN detected
            }

            outdeg = {
                "twitter": 1,
                "reddit": 1,
                "clean": 2,      # ← FANOUT detected
                "sentiment": 1,
                "urgency": 1,
                "logger": 0
            }

        Step 1 - Process FANOUT at clean:
            Detect: clean has out-degree 2
            Insert: Broadcast(num_outports=2) named "broadcast_0"

            Remove edges:
                ("clean", "out", "sentiment", "in")
                ("clean", "out", "urgency", "in")

            Add edges:
                ("clean", "out", "broadcast_0", "in")
                ("broadcast_0", "out_0", "sentiment", "in")
                ("broadcast_0", "out_1", "urgency", "in")

        Step 2 - Process FANIN at clean:
            Detect: clean has in-degree 2
            Insert: MergeAsynch(num_inports=2) named "merge_0"

            Remove edges:
                ("twitter", "out", "clean", "in")
                ("reddit", "out", "clean", "in")

            Add edges:
                ("twitter", "out", "merge_0", "in_0")
                ("reddit", "out", "merge_0", "in_1")
                ("merge_0", "out", "clean", "in")

        Step 3 - Process FANIN at logger:
            Detect: logger has in-degree 2
            Insert: MergeAsynch(num_inports=2) named "merge_1"

            Remove edges:
                ("sentiment", "out", "logger", "in")
                ("urgency", "out", "logger", "in")

            Add edges:
                ("sentiment", "out", "merge_1", "in_0")
                ("urgency", "out", "merge_1", "in_1")
                ("merge_1", "out", "logger", "in")

        Final edges (all 1-to-1):
            [
                ("twitter", "out", "merge_0", "in_0"),
                ("reddit", "out", "merge_0", "in_1"),
                ("merge_0", "out", "clean", "in"),
                ("clean", "out", "broadcast_0", "in"),
                ("broadcast_0", "out_0", "sentiment", "in"),
                ("broadcast_0", "out_1", "urgency", "in"),
                ("sentiment", "out", "merge_1", "in_0"),
                ("urgency", "out", "merge_1", "in_1"),
                ("merge_1", "out", "logger", "in")
            ]

        Final agents (including auto-inserted):
            {
                "twitter": Source(...),
                "reddit": Source(...),
                "merge_0": MergeAsynch(num_inports=2),    # ← INSERTED
                "clean": Transform(...),
                "broadcast_0": Broadcast(num_outports=2),  # ← INSERTED
                "sentiment": Transform(...),
                "urgency": Transform(...),
                "merge_1": MergeAsynch(num_inports=2),    # ← INSERTED
                "logger": Sink(...)
            }

        Visual representation:
            Before:
                twitter ─┐
                         ├─→ clean ─┬─→ sentiment ─┐
                reddit ──┘          └─→ urgency ───┴─→ logger

            After (with auto-inserted nodes):
                twitter ─┐
                         ├─→ merge_0 ─→ clean ─→ broadcast_0 ─┬─→ sentiment ─┐
                reddit ──┘                                     └─→ urgency ───┴─→ merge_1 ─→ logger

        **Key Properties:**
        - All final edges are 1-to-1 connections (each port connected exactly once)
        - Message flow is preserved (semantically equivalent to original intent)
        - Transparent to students (they write simple edges, we handle complexity)
        - Order matters for Merge: first source → in_0, second → in_1, etc.
        """
        # Snapshot original edges for degree computation
        original_edges = list(self.edges)

        names = set(self.nodes)
        for fn, fp, tn, tp in original_edges:
            names.add(fn)
            names.add(tn)
        names = sorted(names)

        # Compute degrees on original graph
        indeg0 = {n: 0 for n in names}
        outdeg0 = {n: 0 for n in names}

        for fn, fp, tn, tp in original_edges:
            outdeg0[fn] += 1
            indeg0[tn] += 1

        # Initial role assignment
        roles: Dict[str, str] = {}
        for n in names:
            if indeg0[n] == 0 and outdeg0[n] == 0:
                raise ValueError(f"Node '{n}' has no incident edges")
            elif indeg0[n] == 0:
                roles[n] = "source"
            elif outdeg0[n] == 0:
                roles[n] = "sink"
            else:
                roles[n] = "transform"

        # Rewrite edges for fanout/fanin
        new_edges = list(original_edges)
        bcount = 0
        mcount = 0

        # Fanout: insert Broadcast for nodes with >1 outgoing
        for n in names:
            outs = [(fn, fp, tn, tp)
                    for (fn, fp, tn, tp) in new_edges if fn == n]
            if len(outs) > 1:
                bname = f"broadcast_{bcount}"
                while bname in roles or bname in self._agents:
                    bcount += 1
                    bname = f"broadcast_{bcount}"
                bcount += 1

                # Create Broadcast agent
                num_outs = len(outs)
                broadcast_agent = Broadcast(num_outports=num_outs)
                self._agents[bname] = broadcast_agent
                roles[bname] = "broadcast"

                # Rewrite edges: n → [outs] becomes n → broadcast → [outs]
                # Remove old edges
                for edge in outs:
                    new_edges.remove(edge)

                # Add n → broadcast
                # Use the port from first outgoing edge
                new_edges.append((n, outs[0][1], bname, "in"))

                # Add broadcast → each target
                for i, (fn, fp, tn, tp) in enumerate(outs):
                    new_edges.append((bname, f"out_{i}", tn, tp))

        # Fanin: insert Merge for nodes with >1 incoming
        for n in names:
            ins = [(fn, fp, tn, tp)
                   for (fn, fp, tn, tp) in new_edges if tn == n]
            if len(ins) > 1:
                mname = f"merge_{mcount}"
                while mname in roles or mname in self._agents:
                    mcount += 1
                    mname = f"merge_{mcount}"
                mcount += 1

                # Create Merge agent
                num_ins = len(ins)
                merge_agent = MergeAsynch(num_inports=num_ins)
                self._agents[mname] = merge_agent
                roles[mname] = "merge"

                # Rewrite edges: [ins] → n becomes [ins] → merge → n
                # Remove old edges
                for edge in ins:
                    new_edges.remove(edge)

                # Add each source → merge
                for i, (fn, fp, tn, tp) in enumerate(ins):
                    new_edges.append((fn, fp, mname, f"in_{i}"))

                # Add merge → n
                # Use the port from first incoming edge
                new_edges.append((mname, "out", n, ins[0][3]))

        # Update edges
        self.edges = new_edges

        # Recompute degrees on final graph
        final_names = set(self._agents.keys())
        self.indeg = {n: 0 for n in final_names}
        self.outdeg = {n: 0 for n in final_names}

        for fn, fp, tn, tp in self.edges:
            self.outdeg[fn] += 1
            self.indeg[tn] += 1

        return roles

    def compile(self) -> Network:
        """
        Compile the graph into an executable Network.

        Steps:
        1. Validate edges reference existing nodes and ports
        2. Infer roles and insert Broadcast/Merge as needed
        3. Build Network with blocks and connections

        Returns:
            Compiled Network ready to run
        """
        # Validate structure
        self._validate_edges()

        # Infer roles and rewrite graph
        roles = self._infer_roles()

        # Build blocks dictionary (all agents are already created)
        blocks: Dict[str, Agent] = {}

        for name, role in roles.items():
            if name in self._agents:
                # Use the agent we already have
                blocks[name] = self._agents[name]
            else:
                raise ValueError(
                    f"Missing agent for node '{name}' with role '{role}'")

        # Build connections (edges are already in the right format)
        connections = self.edges

        # Create Network
        self.network = Network(blocks=blocks, connections=connections)
        return self.network

    def compile_and_run(self) -> None:
        """Compile and run the network."""
        net = self.network or self.compile()
        net.compile_and_run()

    def run_network(self, *args, **kwargs):
        """Run the network (alias for compile_and_run)."""
        return self.compile_and_run(*args, **kwargs)
