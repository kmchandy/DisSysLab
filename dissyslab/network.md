# network.py - Network Construction and Execution

## Purpose

Provides the `Network` class for building, validating, and executing distributed dataflow networks.

**Core Responsibilities:**
1. Container for interconnected agents
2. Validation (all ports connected)
3. Compilation (flatten → resolve → wire → thread)
4. Execution (startup → run → shutdown)
5. Component composition (as_component)

---

## Network Class

### Conceptual Model

A Network is a **container of interconnected agents** that:
- Defines **which agents** exist (blocks dictionary)
- Defines **how they connect** (connections list)
- **Validates** structure (no dangling ports)
- **Compiles** into executable form (threads + queues)
- **Executes** agents concurrently

**Key Insight**: Network is both specification (blocks + connections) and runtime (compiled agents + threads).

### Class Signature

```python
class Network:
    """
    Container of interconnected agents forming a dataflow graph.
    
    A Network represents both:
    - **Specification**: Which agents, how they connect
    - **Runtime**: Compiled threads, queues, execution state
    """
    
    def __init__(
        self,
        *,
        name: Optional[str] = None,
        blocks: Optional[Dict[str, Agent | Network]] = None,
        connections: Optional[List[Tuple[str, str, str, str]]] = None,
        inports: Optional[List[str]] = None,
        outports: Optional[List[str]] = None
    ):
        """
        Create a network.
        
        Args:
            name: Optional name for this network
            blocks: Dict mapping agent names to Agent/Network instances
            connections: List of 4-tuples (from_name, from_port, to_name, to_port)
            inports: External input ports (for nested networks)
            outports: External output ports (for nested networks)
        
        Raises:
            TypeError: If blocks are not Agent/Network instances
            ValueError: If structure is invalid (checked immediately)
        
        Example:
            >>> net = Network(
            ...     blocks={
            ...         "source": Source(fn=gen, name="source"),
            ...         "sink": Sink(fn=save, name="sink")
            ...     },
            ...     connections=[
            ...         ("source", "out_", "sink", "in_")
            ...     ]
            ... )
        """
```

### Data Structures

#### blocks: Dict[str, Agent | Network]
Maps agent names to instances.

```python
blocks = {
    "twitter_feed": Source(...),
    "text_cleaner": Transform(...),
    "database": Sink(...)
}
```

**Invariants:**
- Keys are unique agent names (strings)
- Values are Agent or Network instances
- Names cannot contain "." (reserved for nesting)
- Name "external" is reserved

#### connections: List[Tuple[str, str, str, str]]
List of 4-tuples defining edges.

```python
connections = [
    ("twitter_feed", "out_", "text_cleaner", "in_"),
    ("text_cleaner", "out_", "database", "in_")
]
```

**Format**: `(from_block, from_port, to_block, to_port)`
- `from_block`: Name of sending agent
- `from_port`: Name of sender's output port
- `to_block`: Name of receiving agent  
- `to_port`: Name of receiver's input port

**Invariants:**
- All referenced blocks must exist
- All referenced ports must exist on agents
- Each port connected exactly once (no duplicates, no danglers)

#### inports / outports: List[str]
External ports for component composition.

```python
# Component with external interface
component = Network(
    inports=["data_in", "config_in"],
    outports=["results_out", "errors_out"],
    blocks={...},
    connections=[
        ("external", "data_in", "processor", "in_"),
        ...
        ("formatter", "out_", "external", "results_out")
    ]
)
```

**Purpose:**
- Define component's public interface
- Enable nesting in larger networks
- Connect external inputs to internal agents
- Connect internal agents to external outputs

**Invariants:**
- All declared external ports must be connected
- External connections use "external" as block name

---

## Validation (check method)

### Purpose
Ensure network structure is valid before compilation.

### Validation Rules

#### 1. Block Names
```python
# Valid
blocks = {"source": source_agent, "sink": sink_agent}

# Invalid - contains dot
blocks = {"my.source": source_agent}  # ValueError

# Invalid - reserved name
blocks = {"external": some_agent}  # ValueError
```

#### 2. Block Types
```python
# Valid
blocks = {"src": Source(...), "net": some_network}

# Invalid - not an Agent/Network
blocks = {"bad": "not an agent"}  # TypeError
```

#### 3. Port Connections (1-to-1)
```python
# Valid - each port connected once
connections = [
    ("src", "out_", "trans", "in_"),
    ("trans", "out_", "sink", "in_")
]

# Invalid - trans.out_ connected twice (fanout without Broadcast)
connections = [
    ("src", "out_", "trans", "in_"),
    ("trans", "out_", "sink_a", "in_"),  # trans.out_ → sink_a
    ("trans", "out_", "sink_b", "in_")   # trans.out_ → sink_b (DUPLICATE!)
]
# TypeError: Outport 'out_' of block 'trans' is connected 2 times

# Invalid - sink.in_ not connected (dangling)
connections = [
    ("src", "out_", "trans", "in_")
    # sink.in_ has no connection!
]
# TypeError: Inport 'in_' of block 'sink' is not connected
```

#### 4. Port Existence
```python
# Invalid - port doesn't exist
connections = [
    ("src", "invalid_port", "sink", "in_")
]
# ValueError: Unknown from_port 'invalid_port' on block 'src'
```

#### 5. External Ports
```python
# Valid - external ports connected
net = Network(
    inports=["in"],
    outports=["out"],
    connections=[
        ("external", "in", "processor", "in_"),
        ("processor", "out_", "external", "out")
    ]
)

# Invalid - external port not connected
net = Network(
    inports=["in"],  # Declared but...
    connections=[
        # No connection from external.in!
    ]
)
# ValueError: External inport 'in' is not connected
```

### Error Messages

All validation errors include:
- **What's wrong**: Clear description
- **Where**: Block name, port name
- **Why it's wrong**: Which invariant violated
- **How to fix**: Concrete suggestion

Example:
```
ValueError: Inport 'in_' of block 'processor' is connected 2 times.
Each inport must be connected exactly once.

Conflicting connections:
  ('source_a', 'out_', 'processor', 'in_')
  ('source_b', 'out_', 'processor', 'in_')

Solution: Insert Merge agent to combine inputs:
  merge = MergeAsynch(num_inports=2, name="merge")
  connections = [
      ('source_a', 'out_', 'merge', 'in_0'),
      ('source_b', 'out_', 'merge', 'in_1'),
      ('merge', 'out_', 'processor', 'in_')
  ]
```

---

## Compilation Pipeline

### Overview

Compilation transforms specification → executable runtime:

```
Network (spec)  ──compile()──>  Network (runtime)
  ↓                                ↓
blocks + connections            agents + threads + queues
```

### Steps

#### Step 0: Insert Fanout/Fanin (Pre-processing)

**Purpose**: Maintain 1-to-1 connection invariant

**Problem**: Student writes natural edges with fanout/fanin
```python
connections = [
    ("src", "out_", "trans_a", "in_"),  # src fans out
    ("src", "out_", "trans_b", "in_"),
    ("trans_a", "out_", "sink", "in_"),  # sink fans in
    ("trans_b", "out_", "sink", "in_")
]
# Violates 1-to-1 invariant!
```

**Solution**: Insert Broadcast/Merge automatically
```python
# After insertion:
connections = [
    ("src", "out_", "broadcast_0", "in_"),
    ("broadcast_0", "out_0", "trans_a", "in_"),
    ("broadcast_0", "out_1", "trans_b", "in_"),
    ("trans_a", "out_", "merge_0", "in_0"),
    ("trans_b", "out_", "merge_0", "in_1"),
    ("merge_0", "out_", "sink", "in_")
]
# Now all connections are 1-to-1
```

**Algorithm**:
1. Compute in-degree and out-degree for each (block, port) pair
2. For each port with out-degree > 1: Insert Broadcast
3. For each port with in-degree > 1: Insert Merge
4. Rewrite connections to go through inserted agents
5. Add inserted agents to blocks dictionary

**Transparency**: Students don't see Broadcast/Merge unless debugging

#### Step 1: Flatten Nested Networks

**Purpose**: Expand nested networks into flat list of leaf agents

**Example**:
```python
# Before flattening:
root = Network(
    blocks={
        "component": Network(
            blocks={
                "processor": Transform(...)
            }
        )
    }
)

# After flattening:
root.agents = {
    "root.component.processor": Transform(...)
}
```

**Algorithm**:
```python
def flatten():
    pending = deque([(self, "root")])
    
    while pending:
        network, path = pending.popleft()
        
        for name, block in network.blocks.items():
            full_path = f"{path}.{name}"
            
            if isinstance(block, Agent):
                # Leaf agent - add to agents dict
                agents[full_path] = block
            else:
                # Nested network - add to pending
                pending.append((block, full_path))
                
                # Lift its connections to use full paths
                for conn in block.connections:
                    lifted_conn = lift_connection(conn, full_path)
                    unresolved.append(lifted_conn)
```

**Path Naming**:
- Root: `"root"`
- One level: `"root.agent_name"`
- Two levels: `"root.component.agent_name"`
- N levels: `"root.comp1.comp2...compN.agent_name"`

#### Step 2: Lift Connections

**Purpose**: Convert relative names to full paths

**Example**:
```python
# Component's internal connection (relative):
("processor", "out_", "formatter", "in_")

# After lifting with path "root.component":
("root.component.processor", "out_", "root.component.formatter", "in_")
```

**Special Case: External Connections**
```python
# Component internal connection to external:
("processor", "out_", "external", "out")

# After lifting:
("root.component.processor", "out_", "root.component", "out")
# Note: "external" → path (component's boundary)
```

#### Step 3: Resolve External Connections (Fixpoint)

**Purpose**: Collapse chains through external boundaries

**Problem**: External connections create chains
```python
[
    ("root.src", "out_", "root.comp", "in"),       # src → comp.external.in
    ("root.comp", "in", "root.comp.proc", "in_"),  # comp.external.in → proc
    ("root.comp.proc", "out_", "root.comp", "out"), # proc → comp.external.out
    ("root.comp", "out", "root.sink", "in_")       # comp.external.out → sink
]
```

**Solution**: Collapse chains into direct connections
```python
[
    ("root.src", "out_", "root.comp.proc", "in_"),  # src → proc (direct!)
    ("root.comp.proc", "out_", "root.sink", "in_")  # proc → sink (direct!)
]
```

**Algorithm** (Fixpoint Iteration):
```python
changed = True
while changed:
    changed = False
    
    for conn in unresolved[:]:
        (fb, fp, tb, tp) = conn
        
        # Pattern 1: External-out collapse
        # (A, p) → (B, q) where (B, q) → (C, r)
        # Becomes: (A, p) → (C, r)
        match = find((X, Y, tb, tp) in unresolved)
        if match:
            new_conn = (fb, fp, match.to_block, match.to_port)
            remove(conn)
            remove(match)
            append(new_conn)
            changed = True
            continue
        
        # Pattern 2: External-in collapse
        # (A, p) → (B, q) where (C, r) → (A, p)
        # Becomes: (C, r) → (B, q)
        match = find((X, Y, fb, fp) in unresolved)
        if match:
            new_conn = (match.from_block, match.from_port, tb, tp)
            remove(conn)
            remove(match)
            append(new_conn)
            changed = True
```

**Termination**: Fixpoint reached when no more collapses possible

**Result**: Only direct agent→agent connections remain

#### Step 4: Wire Queues

**Purpose**: Create actual communication channels

**Algorithm**:
```python
# Create one queue per agent inport
for agent in agents.values():
    for inport in agent.inports:
        agent.in_q[inport] = SimpleQueue()

# Connect sender outports to receiver inport queues
for (from_name, from_port, to_name, to_port) in graph_connections:
    sender = agents[from_name]
    receiver = agents[to_name]
    
    # Wire: sender's outport → receiver's inport queue
    sender.out_q[from_port] = receiver.in_q[to_port]
```

**Result**:
- Each agent has queues for all its ports
- Sending agents have references to receiving agents' queues
- Messages flow through shared queues (thread-safe)

#### Step 5: Create Threads

**Purpose**: Enable concurrent execution

```python
for name, agent in agents.items():
    thread = ExceptionThread(
        target=agent.run,
        name=f"{name}_thread",
        daemon=False
    )
    threads.append(thread)
```

**Thread Properties**:
- One thread per agent (1-to-1 mapping)
- Named for debugging (thread name = agent name)
- Non-daemon (network waits for completion)
- Exception capturing (for error reporting)

### Compilation State

After compilation, Network has:
```python
self.compiled = True
self.agents: Dict[str, Agent]           # Flat list of leaf agents
self.graph_connections: List[Connection] # Direct agent→agent edges
self.queues: List[SimpleQueue]          # All inter-agent queues
self.threads: List[ExceptionThread]     # One per agent
```

---

## Execution (run_network method)

### Full Lifecycle

```python
def run_network(self):
    """Compile, start, run, and cleanup network."""
    # 1. Compile (if not already)
    if not self.compiled:
        self.compile()
    
    # 2. Startup all agents
    self.startup()
    
    # 3. Run all agent threads
    self.run()
    
    # 4. Shutdown all agents (even if errors)
    try:
        self.shutdown()
    except:
        pass  # Don't mask run errors with shutdown errors
```

### startup() - Initialization

```python
def startup(self):
    """Call startup() on all agents before threading."""
    for name, agent in self.agents.items():
        try:
            agent.startup()
        except Exception as e:
            raise RuntimeError(f"Startup failed for {name}: {e}")
```

**Purpose**: Initialize resources before threading
- Open files, database connections
- Initialize state that depends on network structure
- Sequential (not threaded yet)

### run() - Concurrent Execution

```python
def run(self):
    """Start all threads and wait for completion."""
    # Start all threads
    for thread in self.threads:
        thread.start()
    
    # Wait for all to complete
    for thread in self.threads:
        thread.join()
    
    # Check for failures
    failed = [t for t in self.threads if t.exception]
    if failed:
        # Report all failures
        for t in failed:
            print(f"Thread {t.name} failed:")
            traceback.print_exception(t.exc_info)
        raise RuntimeError(f"{len(failed)} agent(s) failed")
```

**Properties**:
- All threads start together
- Network blocks until all complete
- Failures reported after all threads joined
- Any exception stops the network

### shutdown() - Cleanup

```python
def shutdown(self):
    """Call shutdown() on all agents after threads complete."""
    errors = []
    
    for name, agent in self.agents.items():
        try:
            agent.shutdown()
        except Exception as e:
            errors.append((name, e))
    
    if errors:
        msgs = "; ".join(f"{n}: {e}" for n, e in errors)
        raise RuntimeError(f"Shutdown failed: {msgs}")
```

**Purpose**: Cleanup resources after execution
- Close files, connections
- Release resources
- Sequential (threading done)
- Errors collected but don't prevent other shutdowns

---

## Component Composition (as_component method)

### Purpose
Convert tested network into reusable component.

### Workflow

```python
# Step 1: Build with test endpoints
inner = network([
    (test_source, processor),
    (processor, test_sink)
])

# Step 2: Test thoroughly
inner.run_network()
assert results_correct()

# Step 3: Convert to component
component = inner.as_component(
    inports=[("in_", test_source)],
    outports=[("out_", test_sink)],
    name="text_processor"
)

# Step 4: Use in production
outer = network([
    (prod_source, component),
    (component, prod_sink)
])
```

### Method Signature

```python
def as_component(
    self,
    inports: List[Tuple[str, Agent | PortReference]] = None,
    outports: List[Tuple[str, Agent | PortReference]] = None,
    name: Optional[str] = None
) -> Network:
    """
    Convert this network into a reusable component.
    
    Replaces boundary agents (test sources/sinks) with external ports.
    
    Args:
        inports: List of (external_port_name, source_agent) tuples
        outports: List of (external_port_name, sink_agent) tuples
        name: Optional name for the component
    
    Returns:
        New Network with external ports
    
    Raises:
        ValueError: If network is already compiled
        ValueError: If specified agents not found in network
    
    Example:
        >>> component = network.as_component(
        ...     inports=[("data_in", test_source)],
        ...     outports=[("results_out", test_sink)],
        ...     name="processor"
        ... )
    """
```

### Algorithm

```python
def as_component(self, inports, outports, name):
    # 1. Parse inports: (external_name, agent) → 4-tuple
    parsed_inports = []
    for ext_name, agent in inports:
        agent_name = find_name(agent)
        port = agent.default_outport
        parsed_inports.append(("external", ext_name, agent_name, port))
    
    # 2. Parse outports: (external_name, agent) → 4-tuple
    parsed_outports = []
    for ext_name, agent in outports:
        agent_name = find_name(agent)
        port = agent.default_inport
        parsed_outports.append((agent_name, port, "external", ext_name))
    
    # 3. Replace edges
    new_connections = list(self.connections)
    agents_to_remove = set()
    
    # Replace inport edges: (agent, port, X, Y) → (external, ext, X, Y)
    for (ext, ext_port, agent, port) in parsed_inports:
        for i, (fn, fp, tn, tp) in enumerate(new_connections):
            if fn == agent and fp == port:
                new_connections[i] = (ext, ext_port, tn, tp)
                agents_to_remove.add(agent)
    
    # Replace outport edges: (X, Y, agent, port) → (X, Y, external, ext)
    for (agent, port, ext, ext_port) in parsed_outports:
        for i, (fn, fp, tn, tp) in enumerate(new_connections):
            if tn == agent and tp == port:
                new_connections[i] = (fn, fp, ext, ext_port)
                agents_to_remove.add(agent)
    
    # 4. Remove boundary agents
    new_blocks = {
        name: agent 
        for name, agent in self.blocks.items()
        if name not in agents_to_remove
    }
    
    # 5. Extract external port names
    inport_names = [ext for (_, ext, _, _) in parsed_inports]
    outport_names = [ext for (_, _, _, ext) in parsed_outports]
    
    # 6. Create component Network
    return Network(
        name=name,
        blocks=new_blocks,
        connections=new_connections,
        inports=inport_names,
        outports=outport_names
    )
```

### Key Transformations

**Before**:
```python
blocks = {
    "test_source": Source(...),
    "processor": Transform(...),
    "test_sink": Sink(...)
}
connections = [
    ("test_source", "out_", "processor", "in_"),
    ("processor", "out_", "test_sink", "in_")
]
```

**After as_component**:
```python
blocks = {
    "processor": Transform(...)
    # test_source and test_sink REMOVED
}
connections = [
    ("external", "in_", "processor", "in_"),    # Boundary replaced
    ("processor", "out_", "external", "out_")   # Boundary replaced
]
inports = ["in_"]
outports = ["out_"]
```

---

## Design Rationale

### Why 4-Tuple Connections?
**Alternative**: Edge objects, Graph classes
**Chosen**: Simple tuples
**Reason**: Minimal, explicit, easy to validate

### Why Immediate Validation?
**Alternative**: Lazy validation during compile
**Chosen**: Validate in __init__
**Reason**: Fail-fast, clearer error messages, safer API

### Why Separate Compile/Run?
**Alternative**: Auto-compile in run_network
**Chosen**: Explicit compile step (but hidden in run_network)
**Reason**: Testing (can inspect compiled state), debugging, flexibility

### Why Insert Fanout/Fanin?
**Alternative**: Require explicit Broadcast/Merge
**Chosen**: Automatic insertion
**Reason**: Natural student syntax, reduces boilerplate, teaches pattern

---

## Testing Networks

### Unit Testing Validation
```python
def test_validation():
    with pytest.raises(ValueError, match="not connected"):
        Network(
            blocks={"source": source, "sink": sink},
            connections=[]  # Missing connection!
        )
```

### Integration Testing Execution
```python
def test_execution():
    results = []
    
    source = Source(fn=lambda: [1, 2, 3], name="src")
    sink = Sink(fn=results.append, name="sink")
    
    net = Network(
        blocks={"src": source, "sink": sink},
        connections=[("src", "out_", "sink", "in_")]
    )
    net.run_network()
    
    assert results == [1, 2, 3]
```

### Property-Based Testing
```python
@given(st.lists(st.integers()))
def test_network_preserves_order(values):
    """Messages arrive in FIFO order."""
    results = []
    
    source = Source(fn=lambda: values, name="src")
    sink = Sink(fn=results.append, name="sink")
    
    net = Network(
        blocks={"src": source, "sink": sink},
        connections=[("src", "out_", "sink", "in_")]
    )
    net.run_network()
    
    assert [r["value"] for r in results] == values
```