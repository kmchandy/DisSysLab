# dsl/core.py
from __future__ import annotations
from queue import SimpleQueue
from threading import Thread
from typing import Optional, List, Dict, Tuple, Union, Any, Protocol
from collections import deque
from abc import ABC, abstractmethod
import sys


# ============================================================================
# Type Definitions
# ============================================================================

# Sentinel object for end-of-stream signaling
class _Stop:
    """Sentinel object for end-of-stream signaling."""

    def __repr__(self):
        return "STOP"


STOP = _Stop()

# Connection tuple: (from_block, from_port, to_block, to_port)
Connection = Tuple[str, str, str, str]

# Type alias for blocks (Agent or Network)
Block = Union["Agent", "Network"]


# ============================================================================
# Port Reference
# ============================================================================

class PortReference:
    """
    Represents an explicit reference to an agent's port.

    Used for explicit port syntax in graph edges:
        (split.out_0, handler) → PortReference(agent=split, port_name="out_0")

    This allows students to explicitly specify which port to connect
    when agents have multiple ports (e.g., Split, custom agents).
    """

    def __init__(self, agent: Agent, port_name: str):
        """
        Initialize a PortReference.

        Args:
            agent: The Agent instance
            port_name: Name of the port (must exist on agent)
        """
        self.agent = agent
        self.port_name = port_name

    def __repr__(self):
        agent_name = self.agent.name if self.agent.name else id(self.agent)
        return f"PortReference({agent_name}.{self.port_name})"

    def __str__(self):
        return f"{self.agent.name}.{self.port_name}"


# ============================================================================
# Protocol for Queue-like Objects
# ============================================================================

class QueueLike(Protocol):
    """Protocol for queue-like objects that support get() and put().

    This allows flexibility in queue implementation - could be SimpleQueue,
    multiprocessing.Queue, or any other queue-like object.
    """

    def get(self) -> Any: ...
    def put(self, item: Any) -> None: ...


# ============================================================================
# Exception-Capturing Thread
# ============================================================================

class ExceptionThread(Thread):
    """Thread that captures exceptions from target function for debugging."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.exception: Optional[Exception] = None
        self.exc_info: Optional[tuple] = None

    def run(self):
        try:
            super().run()
        except Exception as e:
            self.exception = e
            self.exc_info = sys.exc_info()


# ============================================================================
# Agent Base Class
# ============================================================================

class Agent(ABC):
    """
    Base class for all nodes in a flow-based programming network.

    An Agent is a processing unit that:
    - Receives messages on input ports (inports)
    - Processes messages in its run() method
    - Sends messages on output ports (outports)
    - Runs in its own thread when the network executes

    **Lifecycle:**
    1. __init__(): Define ports, initialize state
    2. startup(): One-time initialization before run() (optional override)
    3. run(): Main processing loop (MUST override - abstract method)
    4. shutdown(): Cleanup after run() completes (optional override)

    **Ports:**
    - Inports: Named inputs that receive messages
    - Outports: Named outputs that send messages
    - Each port must be connected exactly once in the network
    - Port names are strings (e.g., "in", "out", "data", "control")

    **Port References:**
    - Access ports explicitly: agent.port_name returns PortReference
    - Used in graph edges: (split.out_0, handler)
    - Enables explicit routing for agents with multiple ports

    **Message Passing:**
    - recv(inport): Blocking read from an input port
    - send(msg, outport): Non-blocking write to an output port
    - Messages can be any Python object, but **dicts are strongly recommended**
    - Using dicts enables the @msg_map decorator pattern (see dsl.decorators)
    - Advanced users may use other types (NumPy arrays, custom classes, etc.)
    - None messages are automatically filtered (not sent downstream)
    - STOP signals indicate end-of-stream and trigger termination

    **Message Convention (recommended):**
    Use dicts with string keys for maximum compatibility with the DSL:
        {"value": 42, "timestamp": 1234567890, "source": "sensor_1"}

    This allows easy use of @msg_map decorators and field-based routing.

    **STOP Signal Handling:**
    - When an agent receives STOP, it should:
      1. Stop processing
      2. Call broadcast_stop() to notify downstream agents
      3. Return from run() to terminate

    **Threading:**
    - Each agent runs in its own thread during network execution
    - Communication between agents is thread-safe via queues
    - No locks needed in agent code - queues handle synchronization
    - Agents should not share mutable state

    **Name Assignment:**
    The `name` attribute is assigned by Network during compilation.
    Do not rely on it in __init__() or before the network is compiled.
    It's primarily used for debugging and error messages.

    **Examples:**

    Simple stateless agent:
        >>> class Doubler(Agent):
        ...     def __init__(self):
        ...         super().__init__(inports=["in"], outports=["out"])
        ...     
        ...     def run(self):
        ...         while True:
        ...             msg = self.recv("in")
        ...             if msg is STOP:
        ...                 self.broadcast_stop()
        ...                 return
        ...             result = {"value": msg["value"] * 2}
        ...             self.send(result, "out")

    Stateful agent with startup/shutdown:
        >>> class FileWriter(Agent):
        ...     def __init__(self, filename):
        ...         super().__init__(inports=["in"], outports=[])
        ...         self.filename = filename
        ...         self.file = None
        ...     
        ...     def startup(self):
        ...         self.file = open(self.filename, 'w')
        ...     
        ...     def run(self):
        ...         while True:
        ...             msg = self.recv("in")
        ...             if msg is STOP:
        ...                 return
        ...             self.file.write(str(msg) + "\\n")
        ...     
        ...     def shutdown(self):
        ...         if self.file:
        ...             self.file.close()

    Agent with multiple ports and explicit references:
        >>> class Split(Agent):
        ...     def __init__(self, num_outputs=3):
        ...         super().__init__(
        ...             inports=["in"],
        ...             outports=[f"out_{i}" for i in range(num_outputs)]
        ...         )
        ...     
        ...     def run(self):
        ...         # Route messages to different outputs
        ...         pass
        >>> 
        >>> split = Split(num_outputs=3)
        >>> # Access ports explicitly:
        >>> split.out_0  # Returns PortReference(split, "out_0")
        >>> split.out_1  # Returns PortReference(split, "out_1")
        >>> split.out_2  # Returns PortReference(split, "out_2")
    """

    def __init__(
        self,
        *,
        inports: Optional[List[str]] = None,
        outports: Optional[List[str]] = None,
    ):
        """
        Initialize an Agent with specified input and output ports.

        Args:
            inports: List of input port names (default: empty list)
            outports: List of output port names (default: empty list)

        Note:
            The name attribute is set by Network during compilation.
            Queues (in_q, out_q) are wired during Network.compile().

        Raises:
            ValueError: If any port names are duplicated within or across inports/outports
        """
        # Avoid mutable-default traps
        self.inports: List[str] = list(inports) if inports is not None else []
        self.outports: List[str] = list(
            outports) if outports is not None else []

        # Validate: all port names must be unique within the agent
        all_ports = self.inports + self.outports
        if len(set(all_ports)) != len(all_ports):
            # Find duplicates
            seen = set()
            duplicates = set()
            for port in all_ports:
                if port in seen:
                    duplicates.add(port)
                seen.add(port)

            raise ValueError(
                f"Port names must be unique within an agent. "
                f"Duplicate port name(s): {sorted(duplicates)}"
            )

        # Queue dictionaries - wired during Network.compile()
        # Values are None until connected, then become QueueLike objects
        self.in_q: Dict[str, Optional[QueueLike]] = {
            p: None for p in self.inports}
        self.out_q: Dict[str, Optional[QueueLike]] = {
            p: None for p in self.outports}

        # Name assigned by Network during compilation
        self.name: Optional[str] = None

    def __getattr__(self, name: str):
        """
        Enable explicit port reference syntax: agent.port_name

        This allows students to write:
            (split.out_0, handler)

        Instead of having to specify ports separately.

        **Important:** All port names must be unique within an agent 
        (across both inports and outports). This is validated in __init__().

        Args:
            name: Port name being accessed

        Returns:
            PortReference for the port

        Raises:
            AttributeError: If the port doesn't exist

        Examples:
            >>> split = Split(num_outputs=3)
            >>> split.out_0  # Returns PortReference(split, "out_0")
            >>> split.out_1  # Returns PortReference(split, "out_1")
            >>> split.invalid  # Raises AttributeError
        """
        # Check if it's a valid port name
        if name in self.inports or name in self.outports:
            return PortReference(agent=self, port_name=name)

        # Not a port, raise normal attribute error
        raise AttributeError(
            f"'{type(self).__name__}' object has no attribute '{name}'. "
            f"Valid ports: inports={self.inports}, outports={self.outports}"
        )

    # ========== Lifecycle Methods ==========

    def startup(self) -> None:
        """
        One-time initialization before run() is called.

        Override this to:
        - Open files or network connections
        - Initialize resources
        - Perform setup that requires the network to be compiled

        Called once per agent before any threads start.
        Exceptions here will prevent the network from starting.
        """
        pass

    @abstractmethod
    def run(self) -> None:
        """
        Main processing loop - MUST be implemented by subclasses.

        This is where the agent does its work:
        - Receive messages from input ports
        - Process data
        - Send results to output ports
        - Handle STOP signals

        Runs in its own thread. Should loop until:
        - STOP signal received, or
        - Processing complete (for sources)

        Typical pattern:
            while True:
                msg = self.recv("in")
                if msg is STOP:
                    self.broadcast_stop()
                    return
                # ... process msg ...
                self.send(result, "out")
        """
        raise NotImplementedError

    def shutdown(self) -> None:
        """
        Cleanup after run() completes.

        Override this to:
        - Close files or network connections
        - Release resources
        - Save final state

        Called once per agent after all threads have joined.
        Exceptions here are logged but don't prevent other agents from shutting down.
        """
        pass

    # ========== Message Passing ==========

    def send(self, msg: Any, outport: str) -> None:
        """
        Send a message to an output port.

        Args:
            msg: Message to send (any Python object, typically a dict)
            outport: Name of the output port

        Behavior:
            - None messages are filtered (not sent downstream)
            - STOP signals pass through
            - Non-blocking operation (queue.put)

        Raises:
            ValueError: If outport doesn't exist or isn't connected
        """
        if outport not in self.outports:
            raise ValueError(
                f"Port '{outport}' is not a valid outport of agent '{self.name}'. "
                f"Valid outports: {self.outports}"
            )

        if outport not in self.out_q:
            raise ValueError(
                f"Outport '{outport}' of agent '{self.name}' has no queue dictionary entry."
            )

        q = self.out_q[outport]
        if q is None:
            raise ValueError(
                f"Outport '{outport}' of agent '{self.name}' is not connected to any queue."
            )

        # Filter out None messages - they are dropped, not sent downstream
        # STOP and all other messages pass through
        if msg is None:
            return

        q.put(msg)

    def recv(self, inport: str) -> Any:
        """
        Receive a message from an input port (blocking).

        Args:
            inport: Name of the input port

        Returns:
            The received message (any Python object, typically a dict)

        Behavior:
            - Blocks until a message is available
            - Returns the message (could be data or STOP signal)

        Raises:
            ValueError: If inport doesn't exist or isn't connected
        """
        if inport not in self.inports:
            raise ValueError(
                f"Port '{inport}' is not a valid inport of agent '{self.name}'. "
                f"Valid inports: {self.inports}"
            )

        if inport not in self.in_q:
            raise ValueError(
                f"Inport '{inport}' of agent '{self.name}' has no queue dictionary entry."
            )

        q = self.in_q[inport]
        if q is None:
            raise ValueError(
                f"Inport '{inport}' of agent '{self.name}' is not connected to any queue."
            )

        return q.get()

    def broadcast_stop(self) -> None:
        """
        Send STOP signal to all downstream agents via all outports.

        Call this when:
        - Receiving STOP from upstream
        - Completing processing (for sources)
        - Encountering an unrecoverable error

        This ensures downstream agents are notified to terminate gracefully.
        """
        for outport in self.outports:
            self.send(STOP, outport)

    # ========== Infrastructure Hooks ==========

    def close(self, inport: str) -> None:
        """
        Logical close hook for an input port.

        Currently a no-op for SimpleQueue. May be used in the future for:
        - Recording closed state
        - Closing file-backed queues
        - Multiprocessing queue cleanup

        Blocks may override to track which inputs have closed.

        Args:
            inport: Name of the input port to close
        """
        return


# ============================================================================
# Network Class
# ============================================================================

class Network:
    """
    Container of interconnected Agents/Networks forming a dataflow graph.

    A Network:
    - Contains blocks (Agents or nested Networks)
    - Defines connections between block ports
    - Can have external input/output ports for composition
    - Validates structure and connectivity
    - Compiles into executable graph with threads and queues
    - Manages agent lifecycle (startup → run → shutdown)

    **Network Structure:**
    - Blocks: Dictionary mapping names to Agent/Network instances
    - Connections: List of 4-tuples (from_block, from_port, to_block, to_port)
    - External ports: Allow networks to be composed hierarchically

    **Connection Rules:**
    - Each port must be connected exactly once (no dangling ports)
    - Connections are 1-to-1 (no implicit fanout/fanin)
    - Block names must be unique, strings, no dots, not "external"
    - "external" is reserved for network's own external ports

    **Compilation Process:**
    1. Flatten: Recursively expand nested networks into leaf agents
    2. Lift: Convert all connections to use full path names
    3. Resolve: Collapse external port chains into agent↔agent edges
    4. Wire: Create queues and connect agent ports
    5. Thread: Create one thread per agent

    **External Ports:**
    Networks can have their own inports/outports for composition:
    - Connect to "external" as the block name
    - Used when embedding networks inside other networks
    - Must be fully connected (validated during check)

    **Example:**

    Simple pipeline:
        >>> from dsl.blocks import Source, Transform, Sink
        >>> 
        >>> source = Source(data=data_source)
        >>> transform = Transform(fn=transformer.run)
        >>> sink = Sink(fn=sink_fn.run)
        >>> 
        >>> net = Network(
        ...     blocks={"src": source, "trans": transform, "snk": sink},
        ...     connections=[
        ...         ("src", "out", "trans", "in"),
        ...         ("trans", "out", "snk", "in")
        ...     ]
        ... )
        >>> 
        >>> net.compile_and_run()

    Network with external ports:
        >>> inner = Network(
        ...     inports=["in"],
        ...     outports=["out"],
        ...     blocks={"doubler": Transform(fn=doubler.run)},
        ...     connections=[
        ...         ("external", "in", "doubler", "in"),
        ...         ("doubler", "out", "external", "out")
        ...     ]
        ... )
        >>> 
        >>> outer = Network(
        ...     blocks={"source": source, "process": inner, "sink": sink},
        ...     connections=[
        ...         ("source", "out", "process", "in"),
        ...         ("process", "out", "sink", "in")
        ...     ]
        ... )
    """

    def __init__(
        self,
        *,
        name: Optional[str] = None,
        inports: Optional[List[str]] = None,
        outports: Optional[List[str]] = None,
        blocks: Optional[Dict[str, Block]] = None,
        connections: Optional[List[Connection]] = None,
    ) -> None:
        """
        Initialize a Network.

        Args:
            name: Optional name for this network
            inports: External input ports (for nested networks)
            outports: External output ports (for nested networks)
            blocks: Dictionary mapping block names to Agent/Network instances
            connections: List of (from_block, from_port, to_block, to_port) tuples

        The network structure is validated immediately via check().
        """
        self.name = name
        self.inports = list(inports) if inports is not None else []
        self.outports = list(outports) if outports is not None else []
        self.blocks: Dict[str, Block] = blocks or {}
        self.connections: List[Connection] = connections or []

        # Assign runtime names to blocks
        for block_name, block_object in self.blocks.items():
            block_object.name = block_name

        # Validate structure
        self.check()

        # Compilation state (populated by compile())
        self.agents: Dict[str, Agent] = {}
        self.graph_connections: List[Connection] = []
        self.queues: List[SimpleQueue] = []
        self.threads: List[ExceptionThread] = []
        self.unresolved_connections: List[Connection] = []

    def check(self) -> None:
        """
        Validate network structure before compilation.

        Ensures:
        - Block names are valid strings (no '.', not 'external')
        - All blocks are Agent or Network instances
        - All connections reference existing blocks and ports
        - Each port is connected exactly once (no dangling or duplicate connections)
        - External ports, if declared, are properly connected

        Raises:
            TypeError: Invalid block or port structure
            ValueError: Invalid names, missing connections, or duplicate connections
        """

        # ========== Validate Block Structure ==========
        for block_name, block_object in self.blocks.items():
            # Block name must be a string
            if not isinstance(block_name, str):
                raise TypeError(
                    f"Block name must be a string, got {type(block_name).__name__}: {block_name!r}"
                )

            # Block name cannot contain '.' (reserved for path separator)
            if "." in block_name:
                raise ValueError(
                    f"Block name '{block_name}' may not contain '.' (reserved for nested paths)"
                )

            # 'external' is reserved for network's own ports
            if block_name == "external":
                raise ValueError(
                    "'external' is reserved and cannot be used as a block name"
                )

            # Block must be Agent or Network
            if not isinstance(block_object, (Agent, Network)):
                raise TypeError(
                    f"Block '{block_name}' must be an Agent or Network instance, "
                    f"got {type(block_object).__name__}"
                )

            # Ports must be lists
            if not isinstance(block_object.inports, list):
                raise TypeError(
                    f"Inports of block '{block_name}' must be a list, "
                    f"got {type(block_object.inports).__name__}"
                )
            if not isinstance(block_object.outports, list):
                raise TypeError(
                    f"Outports of block '{block_name}' must be a list, "
                    f"got {type(block_object.outports).__name__}"
                )

            # Port names must be unique within each block
            if len(set(block_object.inports)) != len(block_object.inports):
                raise ValueError(
                    f"Block '{block_name}' has duplicate inport names: {block_object.inports}"
                )
            if len(set(block_object.outports)) != len(block_object.outports):
                raise ValueError(
                    f"Block '{block_name}' has duplicate outport names: {block_object.outports}"
                )

        # ========== Validate Connection Endpoints ==========
        def _block_exists(b: str) -> bool:
            """Check if block name is valid ('external' or exists in blocks dict)."""
            return b == "external" or b in self.blocks

        for (fb, fp, tb, tp) in self.connections:
            # From-block must exist
            if not _block_exists(fb):
                raise ValueError(
                    f"Connection references unknown from_block '{fb}'. "
                    f"Valid blocks: {list(self.blocks.keys()) + ['external']}"
                )

            # To-block must exist
            if not _block_exists(tb):
                raise ValueError(
                    f"Connection references unknown to_block '{tb}'. "
                    f"Valid blocks: {list(self.blocks.keys()) + ['external']}"
                )

            # From-port must exist on from-block (unless external)
            if fb != "external":
                if fp not in self.blocks[fb].outports:
                    raise ValueError(
                        f"Unknown from_port '{fp}' on block '{fb}'. "
                        f"Valid outports: {self.blocks[fb].outports}"
                    )

            # To-port must exist on to-block (unless external)
            if tb != "external":
                if tp not in self.blocks[tb].inports:
                    raise ValueError(
                        f"Unknown to_port '{tp}' on block '{tb}'. "
                        f"Valid inports: {self.blocks[tb].inports}"
                    )

        # ========== Validate Port Connections (1-to-1) ==========
        for block_name, block_object in self.blocks.items():
            # Each inport must be connected exactly once
            for inport in block_object.inports:
                matches = [
                    c for c in self.connections
                    if c[2] == block_name and c[3] == inport
                ]
                if not matches:
                    raise TypeError(
                        f"Inport '{inport}' of block '{block_name}' is not connected. "
                        f"All inports must be connected exactly once."
                    )
                if len(matches) > 1:
                    raise ValueError(
                        f"Inport '{inport}' of block '{block_name}' is connected {len(matches)} times. "
                        f"Each inport must be connected exactly once. Connections: {matches}"
                    )

            # Each outport must be connected exactly once
            for outport in block_object.outports:
                matches = [
                    c for c in self.connections
                    if c[0] == block_name and c[1] == outport
                ]
                if not matches:
                    raise TypeError(
                        f"Outport '{outport}' of block '{block_name}' is not connected. "
                        f"All outports must be connected exactly once."
                        f"connections are: {self.connections}"
                    )
                if len(matches) > 1:
                    raise ValueError(
                        f"Outport '{outport}' of block '{block_name}' is connected {len(matches)} times. "
                        f"Each outport must be connected exactly once. Connections: {matches}"
                    )

        # ========== Validate External Ports ==========
        # Each declared external inport must be connected exactly once
        for p in self.inports:
            matches = [
                c for c in self.connections
                if c[0] == "external" and c[1] == p
            ]
            if len(matches) == 0:
                raise ValueError(
                    f"External inport '{p}' is not connected. "
                    f"All declared external ports must be connected exactly once."
                )
            if len(matches) > 1:
                raise ValueError(
                    f"External inport '{p}' is connected {len(matches)} times: {matches}. "
                    f"Each external port must be connected exactly once."
                )

        # Each declared external outport must be connected exactly once
        for p in self.outports:
            matches = [
                c for c in self.connections
                if c[2] == "external" and c[3] == p
            ]
            if len(matches) == 0:
                raise ValueError(
                    f"External outport '{p}' is not connected. "
                    f"All declared external ports must be connected exactly once."
                )
            if len(matches) > 1:
                raise ValueError(
                    f"External outport '{p}' is connected {len(matches)} times: {matches}. "
                    f"Each external port must be connected exactly once."
                )

    def compile(self) -> None:
        """
        Flatten nested networks into a graph of agents and wire their queues.

        **Compilation Process:**

        1. **Flatten**: Traverse nested Networks recursively, collect all leaf Agents.
           Each agent gets a full path name based on nesting hierarchy.
           Example: Network "root" → Network "sub" → Agent "worker"
                    Results in agent path "root.sub.worker"

        2. **Lift connections**: Convert all connections to use full path names.
           Example: Connection ("sub", "out") → ("external", "result")
                    Becomes ("root.sub", "out") → ("root", "result")

        3. **Resolve externals**: Repeatedly collapse chains of external connections
           until only direct agent↔agent connections remain (fixpoint iteration).
           Example: (A, p) → (external, x) and (external, x) → (B, q)
                    Collapses to (A, p) → (B, q)

        4. **Wire queues**: Create a SimpleQueue for each agent's inport.
           Connect sender outports to receiver inport queues.
           This establishes the actual communication channels.

        5. **Create threads**: Instantiate one ExceptionThread per agent for
           concurrent execution. Threads will run agent.run() methods.

        **After compilation:**
        - self.agents: Dict mapping full path names to Agent instances
        - self.graph_connections: List of direct agent→agent connections
        - self.queues: All inter-agent SimpleQueues
        - self.threads: One ExceptionThread per agent

        Raises:
            ValueError: If external connections cannot be fully resolved
        """

        class PathNode:
            """Helper for tracking blocks during flattening with their full paths."""

            def __init__(self, block: Block, full_path_name: str):
                self.block = block
                self.full_path_name = full_path_name

        # ========== Step 1: Flatten Nested Networks ==========
        # Breadth-first traversal to find all leaf agents
        root = PathNode(self, "root")
        pending = deque([root])

        while pending:
            node = pending.popleft()
            blk, path = node.block, node.full_path_name

            # If this is a leaf Agent, record it
            if isinstance(blk, Agent):
                self.agents[path] = blk
                continue

            # If this is a Network, add its children to pending
            assert isinstance(blk, Network)
            for child in blk.blocks.values():
                child_path = f"{path}.{child.name}" if path else child.name
                pending.append(PathNode(child, child_path))

            # Lift this network's connections to use full paths
            for (fb, fp, tb, tp) in blk.connections:
                fpath = path if fb == "external" else f"{path}.{fb}"
                tpath = path if tb == "external" else f"{path}.{tb}"
                self.unresolved_connections.append((fpath, fp, tpath, tp))

        # ========== Step 2 & 3: Resolve External Connections (Fixpoint) ==========
        # Repeatedly collapse external chains until no more changes occur
        changed = True
        while changed:
            changed = False
            for conn in self.unresolved_connections[:]:
                fb, fp, tb, tp = conn

                # Pattern 1: External-out collapse
                # (X, p) → (Y, r) where (Y, r) → (Z, s)
                # Becomes: (X, p) → (Z, s)
                match = next(
                    (v for v in self.unresolved_connections
                     if v[0] == tb and v[1] == tp),
                    None
                )
                if match:
                    new_conn = (fb, fp, match[2], match[3])
                    self.unresolved_connections.remove(conn)
                    self.unresolved_connections.remove(match)
                    self.unresolved_connections.append(new_conn)
                    changed = True
                    continue

                # Pattern 2: External-in collapse
                # (W, q) → (X, p) where (Y, r) → (W, q)
                # Becomes: (Y, r) → (X, p)
                match = next(
                    (v for v in self.unresolved_connections
                     if v[2] == fb and v[3] == fp),
                    None
                )
                if match:
                    new_conn = (match[0], match[1], tb, tp)
                    self.unresolved_connections.remove(conn)
                    self.unresolved_connections.remove(match)
                    self.unresolved_connections.append(new_conn)
                    changed = True

        # ========== Extract Direct Agent Connections ==========
        # Keep only connections where both endpoints are actual agents
        for (fb, fp, tb, tp) in self.unresolved_connections[:]:
            if fb in self.agents and tb in self.agents:
                self.unresolved_connections.remove((fb, fp, tb, tp))
                self.graph_connections.append((fb, fp, tb, tp))

        # Any remaining unresolved connections are an error
        if self.unresolved_connections:
            raise ValueError(
                f"Network has unresolved external connections: {self.unresolved_connections}. "
                f"All external ports must be fully connected to agents."
            )

        # ========== Step 4: Wire Queues ==========
        # Create one queue per agent inport
        for agent in self.agents.values():
            for p in agent.inports:
                agent.in_q[p] = SimpleQueue()
                self.queues.append(agent.in_q[p])

        # Connect sender outports to receiver inport queues
        # (1→1 edges already validated by check())
        for (fb, fp, tb, tp) in self.graph_connections:
            sender = self.agents[fb]
            receiver = self.agents[tb]
            sender.out_q[fp] = receiver.in_q[tp]

        # ========== Step 5: Create Threads ==========
        for full_name, agent in self.agents.items():
            t = ExceptionThread(
                target=agent.run,
                name=f"{full_name}_thread",
                daemon=False
            )
            self.threads.append(t)

    def startup(self) -> None:
        """
        Call startup() on all agents before running.

        Allows agents to initialize resources (open files, connections, etc.)
        before their run() methods are called.

        Raises:
            RuntimeError: If any agent's startup() fails
        """
        errors = []
        for name, agent in self.agents.items():
            try:
                agent.startup()
            except Exception as e:
                errors.append((name, e))

        if errors:
            msgs = "; ".join(f"{n}: {repr(e)}" for n, e in errors)
            raise RuntimeError(f"Startup failed for agent(s): {msgs}")

    def shutdown(self) -> None:
        """
        Call shutdown() on all agents after running completes.

        Allows agents to cleanup resources (close files, connections, etc.)
        after their run() methods complete.

        Errors during shutdown are collected but don't prevent other shutdowns.

        Raises:
            RuntimeError: If any agent's shutdown() fails
        """
        errors = []
        for name, agent in self.agents.items():
            try:
                agent.shutdown()
            except Exception as e:
                errors.append((name, e))

        if errors:
            msgs = "; ".join(f"{n}: {repr(e)}" for n, e in errors)
            raise RuntimeError(f"Shutdown failed for agent(s): {msgs}")

    def run(self) -> None:
        """
        Start all agent threads and wait for them to complete.

        Each agent runs in its own thread, executing its run() method.
        This method blocks until all threads have joined.

        If any agent thread raises an exception, it's captured and reported
        after all threads complete, then re-raised for debugging.

        Raises:
            RuntimeError: If any agent thread failed with an exception
        """
        # Start all agent threads
        for t in self.threads:
            t.start()

        # Wait for all threads to complete
        failed_threads = []
        for t in self.threads:
            t.join()
            if hasattr(t, 'exception') and t.exception:
                failed_threads.append(t)

        # Report any failures
        if failed_threads:
            print("\n" + "="*70)
            print("AGENT FAILURES DETECTED:")
            print("="*70)
            for t in failed_threads:
                print(f"\nThread: {t.name}")
                import traceback
                traceback.print_exception(*t.exc_info)
            print("="*70)
            raise RuntimeError(
                f"{len(failed_threads)} agent(s) failed. See traceback above."
            )

    def compile_and_run(self) -> None:
        """
        Convenience method: compile, startup, run, and shutdown the network.

        This is the typical entry point for executing a network:
        1. Compile the network structure
        2. Call startup() on all agents
        3. Run all agents in threads
        4. Call shutdown() on all agents (even if run fails)

        Ensures shutdown is called even if errors occur.
        """
        self.compile()
        try:
            self.startup()
            self.run()
        finally:
            try:
                self.shutdown()
            except Exception:
                pass  # Errors during shutdown don't mask run errors

    def run_network(self, *args, **kwargs):
        """
        Alias for compile_and_run() - provided for compatibility.

        This method name matches common usage patterns in the examples.
        """
        return self.compile_and_run(*args, **kwargs)
