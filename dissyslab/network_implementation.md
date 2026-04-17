# network.py - Implementation Guide

## File Purpose

`dsl/network.py` contains the `Network` class for building, validating, compiling, and executing distributed dataflow networks.

**Core Responsibilities:**
1. Container for interconnected agents
2. Structural validation (all ports connected, no dangling edges)
3. Compilation pipeline (flatten → insert fanout/fanin → resolve → wire → thread)
4. Execution management (startup → run → shutdown)
5. Component composition (as_component method)

## What Goes in network.py

**Include:**
- `Network` class

**Do NOT include:**
- `Agent` base class (in `core.py`)
- Concrete agent types like Source/Transform/Sink (in `blocks/`)
- `network()` builder function (in `builder.py`)
- `PortReference` class (in `builder.py`)
- `Broadcast`/`Merge` agents (in `blocks/`)

---

## Dependencies

```python
from __future__ import annotations
from typing import Optional, List, Dict, Tuple, Any
from queue import SimpleQueue
from collections import deque

from dsl.core import Agent, STOP, ExceptionThread
```

**Note:** Network will need Broadcast/Merge for fanout/fanin insertion, but we'll import them lazily to avoid circular dependencies.

---

## Network Class Structure

```python
class Network:
    """Container of interconnected agents forming a dataflow graph."""
    
    def __init__(
        self,
        *,
        name: Optional[str] = None,
        blocks: Optional[Dict[str, Agent | Network]] = None,
        connections: Optional[List[Tuple[str, str, str, str]]] = None,
        inports: Optional[List[str]] = None,
        outports: Optional[List[str]] = None
    ):
        """Initialize and validate network structure."""
        
    # Validation
    def check(self) -> None:
        """Validate network structure before compilation."""
        
    # Compilation pipeline
    def compile(self) -> None:
        """Compile network into executable form."""
        
    def _insert_fanout_fanin(self) -> None:
        """Insert Broadcast/Merge agents for multi-connections."""
        
    # Execution
    def startup(self) -> None:
        """Call startup() on all agents."""
        
    def run(self) -> None:
        """Start all threads and wait for completion."""
        
    def shutdown(self) -> None:
        """Call shutdown() on all agents."""
        
    def run_network(self) -> None:
        """Compile (if needed), startup, run, and shutdown the network."""
        
    # Component composition
    def as_component(
        self,
        inports: List[Tuple[str, Agent]] = None,
        outports: List[Tuple[str, Agent]] = None,
        name: Optional[str] = None
    ) -> Network:
        """Convert tested network to reusable component."""
```

---

## Implementation Checklist

### 1. Initialization

**Store parameters:**
```python
def __init__(
    self,
    *,
    name: Optional[str] = None,
    blocks: Optional[Dict[str, Agent | Network]] = None,
    connections: Optional[List[Tuple[str, str, str, str]]] = None,
    inports: Optional[List[str]] = None,
    outports: Optional[List[str]] = None
):
    # Store configuration
    self.name = name
    self.inports = list(inports) if inports is not None else []
    self.outports = list(outports) if outports is not None else []
    self.blocks = blocks or {}
    self.connections = connections or []
    
    # Assign names to blocks (for debugging/errors)
    for block_name, block_object in self.blocks.items():
        block_object.name = block_name
    
    # Validate immediately
    self.check()
    
    # Compilation state (populated by compile())
    self.compiled = False
    self.agents: Dict[str, Agent] = {}
    self.graph_connections: List[Tuple[str, str, str, str]] = []
    self.queues: List[SimpleQueue] = []
    self.threads: List[ExceptionThread] = []
    self.unresolved_connections: List[Tuple[str, str, str, str]] = []
```

**Requirements:**
- ✅ All parameters are keyword-only (*)
- ✅ Avoid mutable default trap (use None, then create new lists/dicts)
- ✅ Validate immediately via check()
- ✅ Initialize compilation state variables

### 2. Validation (check method)

**Purpose:** Catch structural errors before compilation

**Validation Rules:**

#### 2.1 Block Names
```python
# Valid block names
for block_name in self.blocks:
    # Must be string
    if not isinstance(block_name, str):
        raise TypeError(f"Block name must be string, got {type(block_name)}")
    
    # Cannot contain '::' (reserved for nested paths)
    if "::" in block_name:
        raise ValueError(
            f"Block name '{block_name}' cannot contain '::' "
            f"(reserved for nested network paths)"
        )
    
    # Cannot be 'external' (reserved)
    if block_name == "external":
        raise ValueError("'external' is reserved and cannot be used as block name")
```

#### 2.2 Block Types
```python
# All blocks must be Agent or Network
for block_name, block_object in self.blocks.items():
    if not isinstance(block_object, (Agent, Network)):
        raise TypeError(
            f"Block '{block_name}' must be Agent or Network, "
            f"got {type(block_object).__name__}"
        )
```

#### 2.3 Port Structure
```python
# Validate port lists
for block_name, block_object in self.blocks.items():
    # Inports must be list
    if not isinstance(block_object.inports, list):
        raise TypeError(
            f"Inports of block '{block_name}' must be list, "
            f"got {type(block_object.inports)}"
        )
    
    # Outports must be list
    if not isinstance(block_object.outports, list):
        raise TypeError(
            f"Outports of block '{block_name}' must be list, "
            f"got {type(block_object.outports)}"
        )
    
    # No duplicate inport names
    if len(set(block_object.inports)) != len(block_object.inports):
        raise ValueError(
            f"Block '{block_name}' has duplicate inport names: "
            f"{block_object.inports}"
        )
    
    # No duplicate outport names
    if len(set(block_object.outports)) != len(block_object.outports):
        raise ValueError(
            f"Block '{block_name}' has duplicate outport names: "
            f"{block_object.outports}"
        )
```

#### 2.4 Connection Endpoints
```python
# All connection endpoints must exist
for (from_block, from_port, to_block, to_port) in self.connections:
    # From-block must exist
    if from_block != "external" and from_block not in self.blocks:
        raise ValueError(
            f"Connection references unknown from_block '{from_block}'. "
            f"Valid blocks: {list(self.blocks.keys()) + ['external']}"
        )
    
    # To-block must exist
    if to_block != "external" and to_block not in self.blocks:
        raise ValueError(
            f"Connection references unknown to_block '{to_block}'. "
            f"Valid blocks: {list(self.blocks.keys()) + ['external']}"
        )
    
    # From-port must exist on from-block (unless external)
    if from_block != "external":
        if from_port not in self.blocks[from_block].outports:
            raise ValueError(
                f"Unknown from_port '{from_port}' on block '{from_block}'. "
                f"Valid outports: {self.blocks[from_block].outports}"
            )
    
    # To-port must exist on to-block (unless external)
    if to_block != "external":
        if to_port not in self.blocks[to_block].inports:
            raise ValueError(
                f"Unknown to_port '{to_port}' on block '{to_block}'. "
                f"Valid inports: {self.blocks[to_block].inports}"
            )
```

#### 2.5 Port Connectivity (IMPORTANT!)

**Before fanout/fanin insertion, connections might have duplicates.**

We should **NOT** validate 1-to-1 connectivity before `_insert_fanout_fanin()`.

Instead, validation happens in two phases:
1. **Before compilation**: Basic structure (blocks exist, ports exist)
2. **After fanout/fanin insertion**: 1-to-1 connectivity

**Revised approach:**
```python
def check(self) -> None:
    """
    Validate basic network structure.
    
    Note: Does NOT check 1-to-1 port connectivity - that happens
    after fanout/fanin insertion during compilation.
    """
    # Validate block names
    # Validate block types
    # Validate port structure
    # Validate connection endpoints exist
    # Validate external ports are connected (if declared)
    
    # DO NOT validate 1-to-1 here - fanout/fanin not inserted yet!
```

#### 2.6 External Port Connectivity
```python
# Each declared external inport must be connected
for p in self.inports:
    matches = [
        c for c in self.connections
        if c[0] == "external" and c[1] == p
    ]
    if len(matches) == 0:
        raise ValueError(
            f"External inport '{p}' is not connected. "
            f"All declared external ports must be connected."
        )

# Each declared external outport must be connected
for p in self.outports:
    matches = [
        c for c in self.connections
        if c[2] == "external" and c[3] == p
    ]
    if len(matches) == 0:
        raise ValueError(
            f"External outport '{p}' is not connected. "
            f"All declared external ports must be connected."
        )
```

**Note:** Multiple connections to external ports are OK (they'll get fanout/fanin inserted).

### 3. Fanout/Fanin Insertion (_insert_fanout_fanin)

**Purpose:** Maintain 1-to-1 connection invariant by inserting Broadcast/Merge agents

**Algorithm:**
```python
def _insert_fanout_fanin(self) -> None:
    """
    Insert Broadcast and Merge agents for multiple connections.
    
    Detects:
    - Fanout: One outport → multiple inports (insert Broadcast)
    - Fanin: Multiple outports → one inport (insert Merge)
    
    Modifies self.connections and self.blocks in place.
    """
    from dsl.blocks import Broadcast, MergeAsynch
    
    # Step 1: Compute in-degree and out-degree for each (block, port)
    out_degree = {}  # (block, port) → count
    in_degree = {}   # (block, port) → count
    
    for (fb, fp, tb, tp) in self.connections:
        out_degree[(fb, fp)] = out_degree.get((fb, fp), 0) + 1
        in_degree[(tb, tp)] = in_degree.get((tb, tp), 0) + 1
    
    # Step 2: Find fanout cases (out-degree > 1)
    fanout_cases = [(b, p) for (b, p), deg in out_degree.items() if deg > 1]
    
    # Step 3: For each fanout, insert Broadcast
    broadcast_count = 0
    for (block, port) in fanout_cases:
        # Find all connections from this port
        outgoing = [
            c for c in self.connections 
            if c[0] == block and c[1] == port
        ]
        
        # Create broadcast agent
        num_outputs = len(outgoing)
        broadcast_name = f"broadcast_{broadcast_count}"
        broadcast = Broadcast(
            num_outputs=num_outputs,
            name=broadcast_name
        )
        self.blocks[broadcast_name] = broadcast
        broadcast_count += 1
        
        # Rewire connections:
        # Before: (block, port) → [(dest1, port1), (dest2, port2), ...]
        # After:  (block, port) → (broadcast, in_)
        #         (broadcast, out_0) → (dest1, port1)
        #         (broadcast, out_1) → (dest2, port2)
        #         ...
        
        # Remove old connections
        for c in outgoing:
            self.connections.remove(c)
        
        # Add new connections
        self.connections.append((block, port, broadcast_name, "in_"))
        for i, (_, _, dest_block, dest_port) in enumerate(outgoing):
            self.connections.append(
                (broadcast_name, f"out_{i}", dest_block, dest_port)
            )
    
    # Step 4: Recompute in-degree (connections changed)
    in_degree = {}
    for (fb, fp, tb, tp) in self.connections:
        in_degree[(tb, tp)] = in_degree.get((tb, tp), 0) + 1
    
    # Step 5: Find fanin cases (in-degree > 1)
    fanin_cases = [(b, p) for (b, p), deg in in_degree.items() if deg > 1]
    
    # Step 6: For each fanin, insert Merge
    merge_count = 0
    for (block, port) in fanin_cases:
        # Find all connections to this port
        incoming = [
            c for c in self.connections
            if c[2] == block and c[3] == port
        ]
        
        # Create merge agent
        num_inputs = len(incoming)
        merge_name = f"merge_{merge_count}"
        merge = MergeAsynch(
            num_inputs=num_inputs,
            name=merge_name
        )
        self.blocks[merge_name] = merge
        merge_count += 1
        
        # Rewire connections:
        # Before: [(src1, port1), (src2, port2), ...] → (block, port)
        # After:  (src1, port1) → (merge, in_0)
        #         (src2, port2) → (merge, in_1)
        #         ...
        #         (merge, out_) → (block, port)
        
        # Remove old connections
        for c in incoming:
            self.connections.remove(c)
        
        # Add new connections
        for i, (src_block, src_port, _, _) in enumerate(incoming):
            self.connections.append(
                (src_block, src_port, merge_name, f"in_{i}")
            )
        self.connections.append((merge_name, "out_", block, port))
        
        merge_count += 1
```

**After this step:**
- ✅ All connections are 1-to-1
- ✅ Broadcast/Merge agents added to self.blocks
- ✅ Connections rewritten to go through Broadcast/Merge

### 4. Compilation Pipeline (compile method)

**High-Level Structure:**

```python
def compile(self) -> None:
    """
    Compile network into executable form.
    
    Pipeline:
    1. Insert fanout/fanin agents (maintain 1-to-1 invariant)
    2. Flatten nested networks to leaf agents
    3. Resolve external connections (collapse chains)
    4. Wire queues between agents
    5. Create execution threads
    6. Validate compiled structure
    """
    if self.compiled:
        return  # Already compiled
    
    # Step 0: Maintain 1-to-1 invariant
    self._insert_fanout_fanin()
    
    # Step 1: Flatten to leaf agents
    self._flatten_networks()
    
    # Step 2: Resolve external port chains
    self._resolve_external_connections()
    
    # Step 3: Wire communication channels
    self._wire_queues()
    
    # Step 4: Create execution threads
    self._create_threads()
    
    # Step 5: Validate compilation succeeded
    self._validate_compiled()
    
    self.compiled = True
```

**Benefits of Modular Structure:**
- ✅ Each step is testable in isolation
- ✅ Clear error messages (know which step failed)
- ✅ Easy to profile performance
- ✅ Simple to extend with new compilation steps
- ✅ Better documentation (each method self-contained)

#### Step 1: _flatten_networks()

```python
def _flatten_networks(self) -> None:
    """
    Flatten nested networks to leaf agents.
    
    Traverses network hierarchy breadth-first, collecting:
    - Leaf agents in self.agents dict (with full paths using :: separator)
    - Lifted connections in self.unresolved_connections
    
    Example:
        Network "root" contains Network "component" contains Agent "processor"
        Results in: self.agents["root::component::processor"] = processor
    
    Modifies:
        - self.agents: Populated with leaf agents
        - self.unresolved_connections: Populated with lifted connections
    """
    class PathNode:
        """Helper for tracking blocks during traversal."""
        def __init__(self, block: Agent | Network, path: str):
            self.block = block
            self.path = path
    
    # Breadth-first traversal starting from root
    root = PathNode(self, "root")
    pending = deque([root])
    
    while pending:
        node = pending.popleft()
        blk, path = node.block, node.path
        
        # Leaf agent - add to agents dict
        if isinstance(blk, Agent):
            self.agents[path] = blk
            continue
        
        # Network - expand children
        assert isinstance(blk, Network)
        for child_name, child_block in blk.blocks.items():
            child_path = f"{path}::{child_name}" if path else child_name
            pending.append(PathNode(child_block, child_path))
        
        # Lift connections to full paths
        for (fb, fp, tb, tp) in blk.connections:
            fpath = path if fb == "external" else f"{path}::{fb}"
            tpath = path if tb == "external" else f"{path}::{tb}"
            self.unresolved_connections.append((fpath, fp, tpath, tp))
```

#### Step 2: _resolve_external_connections()

```python
def _resolve_external_connections(self) -> None:
    """
    Resolve external port chains to direct agent→agent connections.
    
    Uses fixpoint iteration to collapse chains like:
        (A, p) → (external, x) and (external, x) → (B, q)
        Becomes: (A, p) → (B, q)
    
    Two patterns:
    1. External-out: (A, p) → (B, q) where (B, q) → (C, r)
       Collapse to: (A, p) → (C, r)
    
    2. External-in: (A, p) → (B, q) where (C, r) → (A, p)
       Collapse to: (C, r) → (B, q)
    
    Preconditions:
        - self.agents populated with leaf agents
        - self.unresolved_connections has lifted connections
    
    Modifies:
        - self.graph_connections: Populated with direct agent→agent edges
        - self.unresolved_connections: Emptied (all resolved)
    
    Raises:
        ValueError: If external connections cannot be fully resolved
    """
    # Fixpoint iteration - repeat until no changes
    changed = True
    while changed:
        changed = False
        
        for conn in self.unresolved_connections[:]:
            fb, fp, tb, tp = conn
            
            # Pattern 1: External-out collapse
            # (A, p) → (B, q) where (B, q) → (C, r)
            match = next(
                (v for v in self.unresolved_connections
                 if v[0] == tb and v[1] == tp and v != conn),
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
            # (A, p) → (B, q) where (C, r) → (A, p)
            match = next(
                (v for v in self.unresolved_connections
                 if v[2] == fb and v[3] == fp and v != conn),
                None
            )
            if match:
                new_conn = (match[0], match[1], tb, tp)
                self.unresolved_connections.remove(conn)
                self.unresolved_connections.remove(match)
                self.unresolved_connections.append(new_conn)
                changed = True
    
    # Extract direct agent→agent connections
    for (fb, fp, tb, tp) in self.unresolved_connections[:]:
        if fb in self.agents and tb in self.agents:
            self.unresolved_connections.remove((fb, fp, tb, tp))
            self.graph_connections.append((fb, fp, tb, tp))
    
    # Verify all external connections resolved
    if self.unresolved_connections:
        raise ValueError(
            f"Network has unresolved external connections:\n"
            f"{self._format_connections(self.unresolved_connections)}\n"
            f"All external ports must be fully connected to agents."
        )
```

**Note on Fixpoint Iteration Bug:**
The condition `v != conn` prevents matching a connection against itself, avoiding the bug where connections were removed twice.

#### Step 3: _wire_queues()

```python
def _wire_queues(self) -> None:
    """
    Wire communication queues between agents.
    
    For each agent:
    - Creates SimpleQueue for each inport
    - Connects sender outports to receiver inport queues
    
    After this step:
    - All agent.in_q[port] have queue objects
    - All agent.out_q[port] have queue objects (shared with receivers)
    - Agents can call send() and recv()
    
    Preconditions:
        - self.agents populated
        - self.graph_connections has direct agent→agent edges
    
    Modifies:
        - agent.in_q: Populated with SimpleQueue objects
        - agent.out_q: Populated with references to receiver queues
        - self.queues: List of all queues (for cleanup/inspection)
    """
    # Create input queue for each agent inport
    for agent in self.agents.values():
        for port in agent.inports:
            agent.in_q[port] = SimpleQueue()
            self.queues.append(agent.in_q[port])
    
    # Connect sender outports to receiver inport queues
    for (fb, fp, tb, tp) in self.graph_connections:
        sender = self.agents[fb]
        receiver = self.agents[tb]
        sender.out_q[fp] = receiver.in_q[tp]
```

#### Step 4: _create_threads()

```python
def _create_threads(self) -> None:
    """
    Create execution thread for each agent.
    
    Each thread:
    - Runs the agent's run() method
    - Captures exceptions via ExceptionThread
    - Named with agent's full path for debugging
    
    Threads are created but NOT started - use run() to start them.
    
    Preconditions:
        - self.agents populated
    
    Modifies:
        - self.threads: Populated with ExceptionThread objects
    """
    for full_name, agent in self.agents.items():
        t = ExceptionThread(
            target=agent.run,
            name=f"{full_name}_thread",
            daemon=False
        )
        self.threads.append(t)
```

#### Step 5: _validate_compiled()

```python
def _validate_compiled(self) -> None:
    """
    Validate compiled network structure (deep validation).
    
    Called at end of compile() to ensure compilation succeeded.
    Validates the fully flattened, resolved, wired network.
    
    Checks:
    - All agent inports have queues
    - All agent outports have queues
    - No unresolved external connections remain
    - All graph connections reference valid agents
    
    Raises:
        ValueError: If validation fails
    """
    # Verify all agent ports are wired
    for agent_name, agent in self.agents.items():
        # Check all inports connected
        for inport in agent.inports:
            if agent.in_q[inport] is None:
                raise ValueError(
                    f"Compilation failed: Agent '{agent_name}' inport '{inport}' "
                    f"is not connected to any queue."
                )
        
        # Check all outports connected
        for outport in agent.outports:
            if agent.out_q[outport] is None:
                raise ValueError(
                    f"Compilation failed: Agent '{agent_name}' outport '{outport}' "
                    f"is not connected to any queue."
                )
    
    # Verify no unresolved connections remain
    if self.unresolved_connections:
        raise ValueError(
            f"Compilation failed: Unresolved external connections remain:\n"
            f"{self._format_connections(self.unresolved_connections)}"
        )
    
    # Verify all graph connections reference valid agents
    for (fb, fp, tb, tp) in self.graph_connections:
        if fb not in self.agents:
            raise ValueError(
                f"Compilation failed: Connection references unknown agent '{fb}' "
                f"in: {self._format_connection((fb, fp, tb, tp))}"
            )
        if tb not in self.agents:
            raise ValueError(
                f"Compilation failed: Connection references unknown agent '{tb}' "
                f"in: {self._format_connection((fb, fp, tb, tp))}"
            )
```

### 5. Execution Methods

#### startup()
```python
def startup(self) -> None:
    """Call startup() on all agents before running."""
    errors = []
    for name, agent in self.agents.items():
        try:
            agent.startup()
        except Exception as e:
            errors.append((name, e))
    
    if errors:
        msgs = "; ".join(f"{n}: {repr(e)}" for n, e in errors)
        raise RuntimeError(f"Startup failed for agent(s): {msgs}")
```

#### run()
```python
def run(self) -> None:
    """Start all agent threads and wait for completion."""
    # Start all threads
    for t in self.threads:
        t.start()
    
    # Wait for all to complete
    failed_threads = []
    for t in self.threads:
        t.join()
        if hasattr(t, 'exception') and t.exception:
            failed_threads.append(t)
    
    # Report failures
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
```

#### shutdown()
```python
def shutdown(self) -> None:
    """Call shutdown() on all agents after running."""
    errors = []
    for name, agent in self.agents.items():
        try:
            agent.shutdown()
        except Exception as e:
            errors.append((name, e))
    
    if errors:
        msgs = "; ".join(f"{n}: {repr(e)}" for n, e in errors)
        raise RuntimeError(f"Shutdown failed for agent(s): {msgs}")
```

#### run_network() - Main Entry Point
```python
def run_network(self) -> None:
    """
    Compile (if needed), startup, run, and shutdown the network.
    
    This is the main entry point for executing a network.
    Students typically call this after creating a network.
    """
    # Compile if not already compiled
    if not self.compiled:
        self.compile()
    
    try:
        self.startup()
        self.run()
    finally:
        try:
            self.shutdown()
        except Exception:
            pass  # Don't mask run errors with shutdown errors
```

### 6. Component Composition (as_component)

**Purpose:** Convert tested network into reusable component

**Signature:**
```python
def as_component(
    self,
    inports: List[Tuple[str, Agent]] = None,
    outports: List[Tuple[str, Agent]] = None,
    name: Optional[str] = None
) -> Network:
    """
    Convert this network into a reusable component.
    
    Args:
        inports: List of (external_port_name, boundary_agent) tuples
        outports: List of (external_port_name, boundary_agent) tuples
        name: Optional name for the component
    
    Returns:
        New Network with external ports
    
    Raises:
        ValueError: If network is already compiled
        ValueError: If specified agents not found
    """
```

**Implementation:** (From previous session - same as before)
```python
def as_component(self, inports=None, outports=None, name=None):
    if self.compiled:
        raise ValueError(
            "Cannot convert already-compiled network to component"
        )
    
    inports = inports or []
    outports = outports or []
    
    # Parse and validate inports/outports
    # Replace boundary edges
    # Remove boundary agents from blocks
    # Create new Network with external ports
    
    # ... (detailed implementation from previous session)
```

---

## Debug Output Formatting

### User-Facing vs Internal Representation

**Internal (4-tuples):**
```python
self.connections = [
    ("src", "out_", "trans", "in_"),
    ("trans", "out_", "sink", "in_")
]
```

**User-facing (dot notation):**
```python
"src.out_ → trans.in_"
"trans.out_ → sink.in_"
```

### Helper Functions

#### Format Connection for Display
```python
def _format_connection(self, conn: Tuple[str, str, str, str]) -> str:
    """
    Format connection as user-facing string.
    
    Args:
        conn: 4-tuple (from_block, from_port, to_block, to_port)
    
    Returns:
        Formatted string: "from_block.from_port → to_block.to_port"
    """
    from_block, from_port, to_block, to_port = conn
    return f"{from_block}.{from_port} → {to_block}.{to_port}"
```

#### Format Multiple Connections
```python
def _format_connections(self, connections: List[Tuple[str, str, str, str]]) -> str:
    """
    Format list of connections for display.
    
    Returns multiline string with one connection per line.
    """
    if not connections:
        return "  (none)"
    
    lines = []
    for conn in connections:
        lines.append(f"  {self._format_connection(conn)}")
    return "\n".join(lines)
```

### Usage in Error Messages

#### Connection Validation Error
```python
# Bad - shows internal representation
raise ValueError(
    f"Unknown block in connection: {conn}"
)
# Error: Unknown block in connection: ('src', 'out_', 'unknown', 'in_')

# Good - shows user-facing format
raise ValueError(
    f"Unknown block in connection: {self._format_connection(conn)}\n"
    f"Block 'unknown' does not exist in network."
)
# Error: Unknown block in connection: src.out_ → unknown.in_
#        Block 'unknown' does not exist in network.
```

#### Port Validation Error
```python
# Bad
raise ValueError(f"Unknown port '{from_port}' on block '{from_block}'")

# Good
raise ValueError(
    f"Unknown port in connection: {self._format_connection(conn)}\n"
    f"Block '{from_block}' has no outport '{from_port}'.\n"
    f"Valid outports: {self.blocks[from_block].outports}"
)
# Error: Unknown port in connection: src.out_invalid → trans.in_
#        Block 'src' has no outport 'out_invalid'.
#        Valid outports: ['out_']
```

#### Unresolved External Connections
```python
# Bad
raise ValueError(
    f"Network has unresolved external connections: {self.unresolved_connections}"
)

# Good
raise ValueError(
    f"Network has unresolved external connections:\n"
    f"{self._format_connections(self.unresolved_connections)}\n"
    f"All external ports must be fully connected to agents."
)
# Error: Network has unresolved external connections:
#          processor.out_ → external.result
#          external.data_in → analyzer.in_
#        All external ports must be fully connected to agents.
```

#### Fanout/Fanin Insertion (Verbose Mode)
```python
def _insert_fanout_fanin(self, verbose: bool = False) -> None:
    """
    Insert Broadcast and Merge agents.
    
    Args:
        verbose: If True, print what's being inserted
    """
    # ... fanout detection ...
    
    for (block, port) in fanout_cases:
        outgoing = [c for c in self.connections if c[0] == block and c[1] == port]
        
        if verbose:
            print(f"Fanout detected at {block}.{port}:")
            print(f"  Original connections:")
            for conn in outgoing:
                print(f"    {self._format_connection(conn)}")
            print(f"  Inserting Broadcast agent: {broadcast_name}")
        
        # ... insert broadcast ...
        
        if verbose:
            print(f"  New connections:")
            print(f"    {block}.{port} → {broadcast_name}.in_")
            for i in range(num_outputs):
                print(f"    {broadcast_name}.out_{i} → ...")
```

#### Agent Failure Messages
```python
# In run() when threads fail
if failed_threads:
    print("\n" + "="*70)
    print("AGENT FAILURES DETECTED:")
    print("="*70)
    for t in failed_threads:
        # Extract agent name from thread name
        agent_name = t.name.replace("_thread", "")
        
        # Find connections involving this agent
        incoming = [
            self._format_connection(c) 
            for c in self.graph_connections 
            if c[2].endswith(agent_name.split("::")[-1])
        ]
        outgoing = [
            self._format_connection(c)
            for c in self.graph_connections
            if c[0].endswith(agent_name.split("::")[-1])
        ]
        
        print(f"\nFailed agent: {agent_name}")
        if incoming:
            print(f"  Incoming connections:")
            for conn in incoming:
                print(f"    {conn}")
        if outgoing:
            print(f"  Outgoing connections:")
            for conn in outgoing:
                print(f"    {conn}")
        
        print(f"\n  Exception:")
        import traceback
        traceback.print_exception(*t.exc_info)
    print("="*70)
```

### Network Inspection Methods

Provide a single comprehensive method for inspecting network structure:

```python
def show_network(self, verbose: bool = False) -> None:
    """
    Print network structure in user-friendly format.
    
    Shows both pre-compilation (blocks) and post-compilation (agents) state.
    
    Args:
        verbose: If True, show additional details like auto-inserted agents
    """
    print(f"Network: {self.name or '(unnamed)'}")
    print("=" * 70)
    
    # Show blocks (pre-compilation view)
    print(f"\nBlocks ({len(self.blocks)}):")
    for name, block in self.blocks.items():
        block_type = type(block).__name__
        print(f"  {name}: {block_type}")
        if block.inports:
            print(f"    Inports:  {block.inports}")
        if block.outports:
            print(f"    Outports: {block.outports}")
    
    print(f"\nConnections ({len(self.connections)}):")
    if self.connections:
        for conn in self.connections:
            print(f"  {self._format_connection(conn)}")
    else:
        print("  (none)")
    
    # Show external ports if any
    if self.inports:
        print(f"\nExternal Inports: {self.inports}")
    if self.outports:
        print(f"\nExternal Outports: {self.outports}")
    
    # Show compiled state if compiled
    if self.compiled:
        print(f"\n{'=' * 70}")
        print("COMPILED STATE:")
        print("=" * 70)
        
        print(f"\nAgents ({len(self.agents)}):")
        for name, agent in self.agents.items():
            agent_type = type(agent).__name__
            print(f"  {name}: {agent_type}")
        
        print(f"\nAgent Connections ({len(self.graph_connections)}):")
        if self.graph_connections:
            for conn in self.graph_connections:
                print(f"  {self._format_connection(conn)}")
        else:
            print("  (none)")
        
        # Verbose mode - show auto-inserted agents
        if verbose:
            from dsl.blocks import Broadcast, MergeAsynch
            
            auto_inserted = {}
            for name, agent in self.blocks.items():
                if isinstance(agent, (Broadcast, MergeAsynch)):
                    # Check if name follows auto-generated pattern
                    if name.startswith("broadcast_") or name.startswith("merge_"):
                        auto_inserted[name] = agent
            
            if auto_inserted:
                print(f"\nAuto-Inserted Agents ({len(auto_inserted)}):")
                for name, agent in auto_inserted.items():
                    agent_type = type(agent).__name__
                    print(f"  {name}: {agent_type}")
                    
                    # Show what it's doing
                    if isinstance(agent, Broadcast):
                        # Find incoming connection
                        incoming = [
                            self._format_connection(c)
                            for c in self.connections
                            if c[2] == name
                        ]
                        # Find outgoing connections
                        outgoing = [
                            self._format_connection(c)
                            for c in self.connections
                            if c[0] == name
                        ]
                        if incoming:
                            print(f"    Fanout from: {incoming[0]}")
                        if outgoing:
                            print(f"    Broadcasting to {len(outgoing)} destinations")
                    
                    elif isinstance(agent, MergeAsynch):
                        # Find incoming connections
                        incoming = [
                            self._format_connection(c)
                            for c in self.connections
                            if c[2] == name
                        ]
                        # Find outgoing connection
                        outgoing = [
                            self._format_connection(c)
                            for c in self.connections
                            if c[0] == name
                        ]
                        if incoming:
                            print(f"    Fanin from {len(incoming)} sources")
                        if outgoing:
                            print(f"    Merging to: {outgoing[0]}")
    else:
        print(f"\n(Network not yet compiled)")
```

**Usage Examples:**

```python
# Example 1: Inspect before compilation
g = network([
    (source, transform),
    (transform, sink)
])

g.show_network()
# Output:
# Network: (unnamed)
# ======================================================================
# 
# Blocks (3):
#   src: Source
#     Outports: ['out_']
#   trans: Transform
#     Inports:  ['in_']
#     Outports: ['out_']
#   sink: Sink
#     Inports:  ['in_']
#
# Connections (2):
#   src.out_ → trans.in_
#   trans.out_ → sink.in_
#
# (Network not yet compiled)


# Example 2: Inspect after compilation
g = network([
    (source, transform_a),
    (source, transform_b)
])

g.compile()
g.show_network()
# Output:
# Network: (unnamed)
# ======================================================================
# 
# Blocks (4):
#   src: Source
#     Outports: ['out_']
#   trans_a: Transform
#     Inports:  ['in_']
#     Outports: ['out_']
#   trans_b: Transform
#     Inports:  ['in_']
#     Outports: ['out_']
#   broadcast_0: Broadcast
#     Inports:  ['in_']
#     Outports: ['out_0', 'out_1']
#
# Connections (3):
#   src.out_ → broadcast_0.in_
#   broadcast_0.out_0 → trans_a.in_
#   broadcast_0.out_1 → trans_b.in_
#
# ======================================================================
# COMPILED STATE:
# ======================================================================
# 
# Agents (4):
#   root::src: Source
#   root::trans_a: Transform
#   root::trans_b: Transform
#   root::broadcast_0: Broadcast
#
# Agent Connections (3):
#   root::src.out_ → root::broadcast_0.in_
#   root::broadcast_0.out_0 → root::trans_a.in_
#   root::broadcast_0.out_1 → root::trans_b.in_
#
# (Network not yet compiled)


# Example 3: Verbose mode shows auto-inserted details
g.show_network(verbose=True)
# Additional output:
# Auto-Inserted Agents (1):
#   broadcast_0: Broadcast
#     Fanout from: src.out_ → broadcast_0.in_
#     Broadcasting to 2 destinations
```

### Teaching Examples

**Scenario: Student debugging fanout**
```python
g = network([
    (source, handler_a),
    (source, handler_b),
    (source, handler_c)
])

print("Before compilation:")
g.show_network()

print("\nCompiling...")
g.compile()

print("\nAfter compilation (verbose):")
g.show_network(verbose=True)

# Student sees:
# - Original 3 connections
# - Auto-inserted broadcast_0
# - How it rewired the connections
# - Clear before/after comparison
```

---

## Testing Strategy

### Unit Tests for check()
```python
def test_invalid_block_name_with_dot():
    with pytest.raises(ValueError, match="cannot contain"):
        Network(blocks={"my.block": agent})

def test_external_reserved():
    with pytest.raises(ValueError, match="reserved"):
        Network(blocks={"external": agent})

def test_unknown_block_in_connection():
    with pytest.raises(ValueError, match="unknown"):
        Network(
            blocks={"src": source},
            connections=[("src", "out_", "unknown", "in_")]
        )

def test_unknown_port_in_connection():
    with pytest.raises(ValueError, match="Unknown from_port"):
        Network(
            blocks={"src": source, "sink": sink},
            connections=[("src", "invalid", "sink", "in_")]
        )
```

### Integration Tests for Fanout/Fanin
```python
def test_fanout_insertion():
    """Broadcast inserted for one source → two sinks."""
    source = Source(fn=gen, name="src")
    sink_a = Sink(fn=save, name="sink_a")
    sink_b = Sink(fn=save, name="sink_b")
    
    net = Network(
        blocks={"src": source, "sink_a": sink_a, "sink_b": sink_b},
        connections=[
            ("src", "out_", "sink_a", "in_"),
            ("src", "out_", "sink_b", "in_")
        ]
    )
    
    net._insert_fanout_fanin()
    
    # Should have inserted broadcast
    assert "broadcast_0" in net.blocks
    assert isinstance(net.blocks["broadcast_0"], Broadcast)
    
    # Connections should be rewritten
    assert ("src", "out_", "broadcast_0", "in_") in net.connections
    assert ("broadcast_0", "out_0", "sink_a", "in_") in net.connections
    assert ("broadcast_0", "out_1", "sink_b", "in_") in net.connections

def test_fanin_insertion():
    """Merge inserted for two sources → one sink."""
    src_a = Source(fn=gen, name="src_a")
    src_b = Source(fn=gen, name="src_b")
    sink = Sink(fn=save, name="sink")
    
    net = Network(
        blocks={"src_a": src_a, "src_b": src_b, "sink": sink},
        connections=[
            ("src_a", "out_", "sink", "in_"),
            ("src_b", "out_", "sink", "in_")
        ]
    )
    
    net._insert_fanout_fanin()
    
    # Should have inserted merge
    assert "merge_0" in net.blocks
    assert isinstance(net.blocks["merge_0"], MergeAsynch)
```

### Unit Tests for Compilation Steps

```python
def test_flatten_simple_network():
    """Test flattening without nesting."""
    source = Source(fn=gen, name="src")
    sink = Sink(fn=save, name="sink")
    
    net = Network(
        blocks={"src": source, "sink": sink},
        connections=[("src", "out_", "sink", "in_")]
    )
    
    net._insert_fanout_fanin()  # No changes expected
    net._flatten_networks()
    
    # Should have two agents at root level
    assert "root::src" in net.agents
    assert "root::sink" in net.agents
    assert len(net.agents) == 2


def test_flatten_nested_network():
    """Test flattening with nested components."""
    processor = Transform(fn=process, name="proc")
    
    inner = Network(
        blocks={"proc": processor},
        connections=[]
    )
    
    source = Source(fn=gen, name="src")
    outer = Network(
        blocks={"src": source, "component": inner},
        connections=[("src", "out_", "component", "in_")]
    )
    
    outer._flatten_networks()
    
    # Should have flattened to leaf agents with paths
    assert "root::src" in outer.agents
    assert "root::component::proc" in outer.agents
    assert len(outer.agents) == 2


def test_resolve_external_simple():
    """Test resolving simple external chain."""
    agent_a = Transform(fn=lambda x: x, name="A")
    agent_b = Transform(fn=lambda x: x, name="B")
    
    net = Network(
        blocks={"A": agent_a, "B": agent_b},
        connections=[]
    )
    
    # Simulate after flattening
    net.agents = {"root::A": agent_a, "root::B": agent_b}
    net.unresolved_connections = [
        ("root::A", "out_", "external", "temp"),
        ("external", "temp", "root::B", "in_")
    ]
    
    net._resolve_external_connections()
    
    # Should collapse to direct connection
    assert net.graph_connections == [("root::A", "out_", "root::B", "in_")]
    assert len(net.unresolved_connections) == 0


def test_wire_queues():
    """Test queue wiring."""
    agent_a = Transform(fn=lambda x: x, name="A")
    agent_b = Transform(fn=lambda x: x, name="B")
    
    net = Network(
        blocks={"A": agent_a, "B": agent_b},
        connections=[("A", "out_", "B", "in_")]
    )
    
    # Simulate compiled state
    net.agents = {"root::A": agent_a, "root::B": agent_b}
    net.graph_connections = [("root::A", "out_", "root::B", "in_")]
    
    net._wire_queues()
    
    # Verify queues created
    assert agent_a.out_q["out_"] is not None
    assert agent_b.in_q["in_"] is not None
    
    # Verify they're the same queue
    assert agent_a.out_q["out_"] is agent_b.in_q["in_"]


def test_validate_compiled_success():
    """Test validation passes for properly compiled network."""
    agent_a = Source(fn=lambda: [1], name="A")
    agent_b = Sink(fn=lambda x: None, name="B")
    
    net = Network(
        blocks={"A": agent_a, "B": agent_b},
        connections=[("A", "out_", "B", "in_")]
    )
    
    net.compile()
    
    # Should not raise
    net._validate_compiled()


def test_validate_compiled_missing_queue():
    """Test validation fails if queue not wired."""
    agent = Transform(fn=lambda x: x, name="trans")
    
    net = Network(blocks={"trans": agent}, connections=[])
    net.agents = {"root::trans": agent}
    net.graph_connections = []
    
    # Don't wire queues - should fail validation
    with pytest.raises(ValueError, match="not connected"):
        net._validate_compiled()


def test_validate_compiled_unresolved():
    """Test validation fails if external connections unresolved."""
    net = Network(blocks={}, connections=[])
    net.agents = {}
    net.unresolved_connections = [
        ("external", "in_", "missing", "port")
    ]
    
    with pytest.raises(ValueError, match="Unresolved external"):
        net._validate_compiled()
```

### Integration Tests for Compilation
```python
def test_simple_pipeline_compilation():
    """Test compiling simple source → transform → sink."""
    results = []
    
    source = Source(fn=lambda: [1, 2, 3], name="src")
    transform = Transform(fn=lambda x: x * 2, name="trans")
    sink = Sink(fn=results.append, name="sink")
    
    net = Network(
        blocks={"src": source, "trans": transform, "sink": sink},
        connections=[
            ("src", "out_", "trans", "in_"),
            ("trans", "out_", "sink", "in_")
        ]
    )
    
    net.compile()
    
    # Check compilation state
    assert net.compiled
    assert len(net.agents) == 3
    assert len(net.threads) == 3
    assert len(net.queues) == 2  # One per agent inport

def test_full_execution():
    """Test complete network execution."""
    results = []
    
    source = Source(fn=lambda: [1, 2, 3], name="src")
    double = Transform(fn=lambda x: x * 2, name="dbl")
    sink = Sink(fn=results.append, name="sink")
    
    net = Network(
        blocks={"src": source, "dbl": double, "sink": sink},
        connections=[
            ("src", "out_", "dbl", "in_"),
            ("dbl", "out_", "sink", "in_")
        ]
    )
    
    net.run_network()
    
    assert results == [2, 4, 6]
```

---

## Common Pitfalls

### 1. Validating 1-to-1 Before Fanout/Fanin
**Problem:** check() validates 1-to-1 connectivity, but fanout/fanin not inserted yet
**Solution:** Only validate basic structure in check(), defer 1-to-1 until after insertion

### 2. Modifying List While Iterating
**Problem:** `for c in self.connections: self.connections.remove(c)`
**Solution:** Iterate over copy: `for c in self.connections[:]:`

### 3. Circular Import (Network ↔ Broadcast/Merge)
**Problem:** Network needs Broadcast/Merge, but they import Network for as_component
**Solution:** Lazy import inside _insert_fanout_fanin method

### 4. Forgetting to Mark Compiled
**Problem:** compile() can be called multiple times, duplicating work
**Solution:** Check `if self.compiled: return` at start of compile()

### 5. Fixpoint Iteration Bug
**Problem:** Removing same connection twice in resolve step
**Solution:** Add `v != conn` check when finding matches

---

## Questions to Resolve

1. **Should Network have inports/outports attributes if not used as component?**
   - Current: Always initialized (empty lists by default)
   - This is fine - simplifies logic

2. **Auto-compile in run_network()?**
   - Current: Yes, checks `if not self.compiled: self.compile()`
   - This is good for student convenience

3. **Error verbosity for fanout/fanin?**
   - Should we tell students "We inserted broadcast_0 here"?
   - Or keep it transparent?
   - Recommend: Add logging/verbose mode option

4. **Should blocks dict be modified during fanout/fanin insertion?**
   - Current: Yes, Broadcast/Merge added directly
   - Alternative: Keep separate "inserted_agents" dict
   - Current approach is simpler

---

## Implementation Order

1. **__init__** - Store parameters, call check()
2. **check()** - Shallow validation (structure only)
3. **_insert_fanout_fanin()** - Insert Broadcast/Merge agents
4. **_flatten_networks()** - Expand nested networks to leaf agents
5. **_resolve_external_connections()** - Collapse external port chains
6. **_wire_queues()** - Create and connect communication queues
7. **_create_threads()** - Create execution threads for agents
8. **_validate_compiled()** - Deep validation after compilation
9. **compile()** - Main pipeline that calls steps 3-8
10. **startup/run/shutdown** - Execution management
11. **run_network** - Convenience method (compile → startup → run → shutdown)
12. **_format_connection/_format_connections** - Debug helpers
13. **show_network** - Inspection method (shows both pre/post compilation state)
14. **as_component** - Component composition (can defer to later)

---