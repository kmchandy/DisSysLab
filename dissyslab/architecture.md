# DisSysLab DSL Architecture

## Overview

This document describes the architecture of the DisSysLab Domain-Specific Language (DSL) for building distributed dataflow networks. The DSL allows students to create concurrent agent networks using ordinary Python functions without explicit concurrency primitives.

## Design Philosophy

### Core Principles

1. **Simplicity First**: Minimize concepts students must learn
2. **Fail-Fast**: Catch errors early with clear messages
3. **Pedagogical Value**: Code structure teaches distributed systems concepts
4. **Type Safety**: Use Python's type system to prevent errors
5. **Explicit Over Implicit**: Named agents, explicit ports when needed

### Key Design Decisions

#### 1. Named Agents Required
Every agent must have a unique name provided at construction:
```python
source = Source(fn=generate_data, name="twitter_feed")
transform = Transform(fn=clean_text, name="cleaner")
sink = Sink(fn=save_to_db, name="database")
```

**Rationale:**
- Makes debugging trivial (see agent name in error messages)
- Self-documenting code (names describe purpose)
- Enables clear visualization and logging
- Forces students to think about what each agent does
- Professional practice (systems in production need identifiable components)

**Rejected Alternative:** Auto-generated names (UUIDs or sequential numbers)
- UUIDs are impossible to debug: "Error in Transform@f47ac10b..."
- Sequential names lack meaning: "transform_0" tells you nothing

#### 2. Single Network Class (No Graph Abstraction)
The `network()` function directly creates `Network` objects:
```python
g = network([
    (source, transform),
    (transform, sink)
])
```

**Rationale:**
- Eliminates unnecessary abstraction layer
- Students learn one concept: Network
- All compilation logic in one place
- Simpler mental model: edges → Network → run

**Rejected Alternative:** Graph → Network pipeline
- Graph class adds indirection without value
- Duplicates validation and compilation logic
- Students must understand two classes instead of one

#### 3. Fanout/Fanin Handled Transparently
Students write natural edges; framework inserts Broadcast/Merge automatically:
```python
g = network([
    (source, transform_a),  # Fanout: source sends to both
    (source, transform_b),
    (transform_a, sink),    # Fanin: both send to sink
    (transform_b, sink)
])
```

**Rationale:**
- Students focus on dataflow, not mechanics
- Framework ensures 1-to-1 connections (required invariant)
- Transparent: works correctly without student intervention
- Teaches pattern: explicit fanout/fanin agents when needed

#### 4. Default Ports with Explicit Override
Agents have sensible defaults but support explicit syntax:
```python
# Simple case: use defaults
(source, transform)  # source.out_ → transform.in_

# Complex case: explicit ports
(splitter.out_0, handler_a)  # splitter.out_0 → handler_a.in_
(splitter.out_1, handler_b)  # splitter.out_1 → handler_b.in_
```

**Rationale:**
- 90% of edges are simple: default makes them clean
- 10% need explicit control: dot notation provides it
- Self-documenting: explicit syntax shows routing
- Flexible: works for any port configuration

#### 5. Components Are Networks
No special Component class; networks can be nested:
```python
# Build and test
inner = network([...])
inner.run_network()  # Test it

# Convert to component
component = inner.as_component(
    inports=[("in_", source)],
    outports=[("out_", sink)]
)

# Use in larger network
outer = network([
    (big_source, component),
    (component, big_sink)
])
```

**Rationale:**
- Uniform abstraction: everything is a Network
- Natural composition: use components like agents
- Leverages existing compilation machinery
- Clear progression: build → test → externalize → reuse

---

## Architecture Layers

### Layer 1: Core Abstractions (core.py)

**Purpose:** Define fundamental building blocks

**Contains:**
- `STOP`: Sentinel for end-of-stream signaling
- `Agent`: Abstract base class for all processing nodes
- Port management and message passing primitives

**Key Concepts:**
- **Agent Lifecycle**: `startup()` → `run()` → `shutdown()`
- **Message Passing**: `send(msg, port)` and `recv(port)`
- **Threading**: Each agent runs in its own thread
- **Ports**: Named input/output channels for messages

**Invariants:**
- Each port connected exactly once (validated by Network)
- Messages are dicts (recommended) or any Python object
- None messages are filtered (dropped, not sent)
- STOP propagates through network to trigger termination

### Layer 2: Network Construction (network.py)

**Purpose:** Build, validate, and execute networks

**Contains:**
- `Network`: Container for interconnected agents
- Validation logic (check all ports connected)
- Compilation pipeline (flatten → resolve → wire → thread)
- Fanout/fanin insertion (Broadcast/Merge injection)

**Key Concepts:**
- **Blocks**: Dictionary mapping names to Agent/Network instances
- **Connections**: List of 4-tuples `(from_name, from_port, to_name, to_port)`
- **External Ports**: Declared inports/outports for component composition
- **Nested Networks**: Recursive flattening during compilation

**Compilation Pipeline:**
1. **Validate**: Check all ports connected, no dangling edges
2. **Insert Fanout/Fanin**: Maintain 1-to-1 connection invariant
3. **Flatten**: Recursively expand nested networks to leaf agents
4. **Resolve**: Collapse external port chains into direct connections
5. **Wire**: Create queues and connect agent ports
6. **Thread**: Create one thread per agent for concurrent execution

### Layer 3: Convenient Builders (builder.py)

**Purpose:** Provide natural syntax for network construction

**Contains:**
- `network(edges)`: Build Network from edge list
- `PortReference`: Represents explicit port references (agent.port)
- Edge parsing logic

**Key Concepts:**
- **2-Tuple Edges**: `(from_node, to_node)` where nodes are Agent/Network/PortReference
- **Default Ports**: Automatically use `out_` and `in_` when unambiguous
- **Dot Notation**: `agent.port_name` for explicit port specification
- **Uniform Syntax**: Same syntax for agents and components

### Layer 4: Component Composition (component.py or network.py)

**Purpose:** Support build-test-externalize-reuse workflow

**Contains:**
- `Network.as_component()`: Convert tested network to reusable component
- Helper functions for port parsing

**Key Concepts:**
- **Test Endpoints**: Original network has concrete sources/sinks
- **External Ports**: Component has abstract input/output interfaces
- **Boundary Replacement**: Test endpoints → external port references
- **Nesting**: Components can contain components (arbitrary depth)

---

## File Organization

```
dsl/
├── README.md                    # This file
├── __init__.py                  # Public API exports
├── core.py                      # Agent base class, STOP, message passing
├── network.py                   # Network class, compilation, execution
├── builder.py                   # network() function, edge parsing
├── ports.py                     # PortReference, port utilities
└── blocks/                      # Pre-built agent types
    ├── __init__.py
    ├── source.py                # Source agent
    ├── transform.py             # Transform agent
    ├── sink.py                  # Sink agent
    ├── broadcast.py             # Broadcast (fanout) agent
    ├── merge.py                 # Merge (fanin) agent
    └── split.py                 # Split (routing) agent
```

---

## Public API

### Building Networks

```python
from dsl import network
from dsl.blocks import Source, Transform, Sink

# Create agents with REQUIRED names
source = Source(fn=data_generator, name="twitter_feed")
cleaner = Transform(fn=clean_text, name="text_cleaner")
analyzer = Transform(fn=analyze_sentiment, name="sentiment_analyzer")
sink = Sink(fn=save_results, name="database_writer")

# Build network from edges
g = network([
    (source, cleaner),
    (cleaner, analyzer),
    (analyzer, sink)
])

# Run it
g.run_network()
```

### Explicit Port Syntax

```python
from dsl.blocks import Split

# Create splitter with multiple outputs
splitter = Split(router=route_fn, num_outputs=3, name="classifier")

# Use explicit port syntax
g = network([
    (source, splitter),
    (splitter.out_0, urgent_handler),    # High priority → handler 0
    (splitter.out_1, normal_handler),    # Normal priority → handler 1
    (splitter.out_2, low_handler)        # Low priority → handler 2
])
```

### Component Composition

```python
# Step 1: Build and test network
inner = network([
    (test_source, processor),
    (processor, test_sink)
])
inner.run_network()  # Verify it works

# Step 2: Convert to reusable component
component = inner.as_component(
    inports=[("in_", test_source)],
    outports=[("out_", test_sink)],
    name="text_processor"
)

# Step 3: Use in larger network
outer = network([
    (production_source, component),
    (component, production_sink)
])
outer.run_network()
```

### Nested Components

```python
# Build component A
component_a = network_a.as_component(...)

# Build component B
component_b = network_b.as_component(...)

# Compose them
pipeline = network([
    (source, component_a),
    (component_a, component_b),
    (component_b, sink)
])

# Entire pipeline can become a component
mega_component = pipeline.as_component(
    inports=[("in_", source)],
    outports=[("out_", sink)]
)
```

---

## Message Format

### Philosophy: Use the Right Type for Your Data

Messages can be **any pickleable Python object**. Choose the type that best fits your application:

**Simple values** - Use primitives when you only need the value:
```python
msg = 42                    # Integer
msg = "Hello world"         # String
msg = 3.14159              # Float
msg = np.array([1, 2, 3])  # NumPy array
```

**Multiple values** - Use tuples for simple grouping:
```python
msg = (42, "metadata", 1234567890)  # (value, description, timestamp)
```

**Named fields** - Use dicts when field names add clarity:
```python
msg = {"text": "Hello", "timestamp": 1234567890, "source": "twitter"}
```

**Type safety** - Use dataclasses for complex domains:
```python
@dataclass
class SensorReading:
    temperature: float
    humidity: float
    timestamp: int

msg = SensorReading(72.5, 45, 1234567890)
```

### When to Use Each Type

**Use primitives when:**
- Processing single values (numbers, strings, arrays)
- Building numeric pipelines (image processing, ML)
- Simplicity is paramount

**Use dicts when:**
- You need to add metadata progressively through the pipeline
- Field names make the code self-documenting
- You want to preserve context alongside data
- Routing decisions depend on message fields

**Use custom types when:**
- You need strong type checking
- The domain is complex with many fields
- You want IDE autocomplete support

### Design Guideline

Start simple (primitives), add structure (dicts/classes) only when needed:
```python
# Start simple
yield 42

# Add metadata when it becomes useful
yield {"value": 42, "timestamp": time.time()}

# Add type safety when complexity demands it
yield SensorReading(value=42, timestamp=time.time(), source="sensor_1")
```

---

## Error Messages

### Philosophy: Fail Fast with Clear Context

All errors include:
1. **What went wrong**: Brief description
2. **Where it happened**: Agent name, port name
3. **Why it's a problem**: Explain the invariant violated
4. **How to fix it**: Suggest concrete solutions

### Examples

**Missing agent name:**
```
ValueError: Agent name is required for Source.
Provide name parameter: Source(fn=..., name="my_source")
```

**Dangling port:**
```
TypeError: Outport 'out_' of agent 'cleaner' is not connected.
All outports must be connected exactly once.

Available connections:
  ('cleaner', 'out_', ???, ???)

Add connection:
  (cleaner, some_downstream_agent)
```

**Multiple connections to same port:**
```
Note: Multiple connections to the same port are automatically handled.

The framework detects fanout (one output → multiple inputs):
  ('transform', 'out_', 'sink_a', 'in_')
  ('transform', 'out_', 'sink_b', 'in_')

Auto-inserted Broadcast agent:
  ('transform', 'out_', 'broadcast_0', 'in_')
  ('broadcast_0', 'out_0', 'sink_a', 'in_')
  ('broadcast_0', 'out_1', 'sink_b', 'in_')

For fanin (multiple outputs → one input), Merge is auto-inserted.
To use custom broadcast/merge logic, create agents explicitly.
```

**Port doesn't exist:**
```
ValueError: Agent 'splitter' has no outport 'out_5'
Valid outports: ['out_0', 'out_1', 'out_2']

Did you mean one of these?
  splitter.out_0
  splitter.out_1
  splitter.out_2
```

---

## Testing Strategy

### Unit Tests

**Core Components:**
- `Agent`: Lifecycle, message passing, STOP handling
- `Network`: Validation, compilation, execution
- `PortReference`: Attribute access, representation

**Edge Cases:**
- Empty networks
- Single-agent networks
- Cyclic connections (when supported)
- Deeply nested components (5+ levels)

### Integration Tests

**Patterns:**
- Linear pipelines (A → B → C)
- Fanout (A → B, A → C)
- Fanin (A → C, B → C)
- Diamond (A → B → D, A → C → D)
- Multi-level components

**Real Scenarios:**
- RSS feed → cleaner → sentiment analyzer → database
- Multiple sources → merger → processor → multiple sinks
- Component containing component containing component

### Property-Based Tests

**Invariants to verify:**
- Every port connected exactly once (after compilation)
- STOP propagates to all reachable agents
- Message delivery is FIFO per connection
- No deadlocks in acyclic networks
- Compilation is idempotent

---

## Performance Characteristics

### Not Optimized For Performance

**Design Priority:** Teaching > Performance

**Why:**
- Thread-per-agent is pedagogically clear but inefficient
- SimpleQueue has overhead
- No batching or backpressure
- No work stealing or load balancing

**Acceptable Use Cases:**
- Teaching examples (< 100 agents)
- Prototyping distributed algorithms
- Small-scale data processing

**Not Suitable For:**
- Production data pipelines
- High-throughput systems
- Low-latency applications
- Large-scale deployments

### When Students Need Performance

**Teach the concepts first** (with this framework), then:
1. Show production systems (Apache Kafka, Ray, Dask)
2. Explain optimizations (batching, backpressure, thread pools)
3. Compare trade-offs (simplicity vs performance)

This framework is a **teaching tool**, not a production system.

---

## Extension Points

### Adding New Agent Types

```python
class MyCustomAgent(Agent):
    """Custom agent for specialized processing."""
    
    def __init__(self, *, name, param1, param2):
        super().__init__(
            name=name,
            inports=["in_"],
            outports=["out_", "error_"]  # Multiple outputs
        )
        self.param1 = param1
        self.param2 = param2
    
    def run(self):
        while True:
            msg = self.recv("in_")
            if msg is STOP:
                self.broadcast_stop()
                return
            
            try:
                result = self._process(msg)
                self.send(result, "out_")
            except Exception as e:
                error_msg = {"error": str(e), "original": msg}
                self.send(error_msg, "error_")
    
    def _process(self, msg):
        # Custom processing logic
        pass
```

### Adding New Decorators

Since messages can be any type, decorators can provide convenient wrappers for common patterns:

```python
def simple_transform(fn):
    """Wrap a function as a Transform agent."""
    class WrappedTransform(Transform):
        def __init__(self, name):
            super().__init__(fn=fn, name=name)
    return WrappedTransform

# Usage
@simple_transform
def double(value):
    return value * 2

doubler = double(name="doubler")
```

### Custom Compilation Steps

```python
class CustomNetwork(Network):
    """Network with custom compilation behavior."""
    
    def compile(self):
        # Custom pre-processing
        self._custom_validation()
        
        # Standard compilation
        super().compile()
        
        # Custom post-processing
        self._inject_monitoring()
    
    def _custom_validation(self):
        # Add domain-specific checks
        pass
    
    def _inject_monitoring(self):
        # Add logging, metrics, etc.
        pass
```

---

## Future Directions

### Planned Features
1. **Cycle Support**: Enable feedback loops with global snapshots
2. **Backpressure**: Flow control for bounded queues
3. **Visualization**: Auto-generate network diagrams
4. **Debugging**: Step-through execution, message tracing
5. **Metrics**: Built-in throughput and latency tracking

### Research Questions
1. Can we support both sync and async agents?
2. How to handle time in distributed systems?
3. Best way to express distributed algorithms (consensus, leader election)?
4. Integration with distributed runtimes (Ray, Dask)?

---

## Related Concepts

### Flow-Based Programming (FBP)
This DSL is inspired by FBP principles:
- Agents as black boxes
- Message passing via ports
- Explicit connections (edges)
- Concurrent execution

### Actor Model
Similarities:
- Agents = Actors (independent units)
- Message passing for communication
- No shared mutable state

Differences:
- FBP has explicit structure (graph)
- Actors are more dynamic
- FBP emphasizes dataflow

### Dataflow Programming
Core idea: Computation triggered by data availability
- Agents process when input arrives
- Results flow to downstream agents
- Parallelism is implicit (exposed by graph structure)

---

## Glossary

**Agent**: Independent processing unit that runs in its own thread

**Block**: Agent or Network (used in Network.blocks dictionary)

**Broadcast**: Agent that copies input to multiple outputs (fanout)

**Component**: Network with external ports, used as building block

**Connection**: 4-tuple specifying edge between ports

**Edge**: Link between two agents in the network

**External Port**: Input/output port of a Network for composition

**Fanin**: Multiple agents sending to one receiver (requires Merge)

**Fanout**: One agent sending to multiple receivers (requires Broadcast)

**Merge**: Agent that combines multiple inputs into one stream (fanin)

**Message**: Data passed between agents (typically a dict)

**Network**: Container of interconnected agents

**Port**: Named channel for sending/receiving messages

**PortReference**: Object representing explicit port reference (agent.port)

**Sink**: Agent with only inputs (terminal node)

**Source**: Agent with only outputs (starting node)

**STOP**: Sentinel signaling end-of-stream

**Transform**: Agent with inputs and outputs (processing node)