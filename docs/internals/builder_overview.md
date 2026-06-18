# builder.py - Network Construction Helpers

## Purpose

Provides natural syntax for building networks from edge lists:
- `network(edges)`: Main entry point for students
- `PortReference`: Enables dot notation for explicit ports
- Edge parsing: Convert 2-tuples to Network structure

---

## network() Function

### Purpose
Build a Network from a list of edges using natural syntax.

### Signature

```python
def network(edges: List[Tuple[EdgeNode, EdgeNode]]) -> Network:
    """
    Build a Network from edge list.
    
    Args:
        edges: List of 2-tuples (from_node, to_node) where nodes can be:
               - Agent instances (use default ports)
               - Network instances (use single external port)
               - PortReference (explicit port: agent.port_name)
    
    Returns:
        Network ready to run
    
    Raises:
        TypeError: If edge format is invalid
        ValueError: If agents have no default ports
        ValueError: If agent names are not unique
    
    Example:
        >>> g = network([
        ...     (source, transform),      # Simple: use defaults
        ...     (transform, sink)
        ... ])
        >>> g.run_network()
    """
```

### Edge Syntax

#### Simple Syntax (Default Ports)
```python
# Most common case: single input/output
g = network([
    (source, transform),   # source.out_ → transform.in_
    (transform, sink)      # transform.out_ → sink.in_
])
```

**When it works:**
- Agent has single obvious input/output
- Agent defines `default_inport` / `default_outport` properties

**When it fails:**
```python
splitter = Split(num_outputs=3, name="split")

g = network([
    (source, splitter),      # ✓ Works: splitter.in_ (default)
    (splitter, handler)      # ✗ Fails: which output? out_0, out_1, out_2?
])
# ValueError: Agent 'split' has no default outport
```

#### Explicit Syntax (Dot Notation)
```python
# Complex case: multiple ports
g = network([
    (source, splitter),          # Use defaults where possible
    (splitter.out_0, urgent),    # Explicit: route to urgent handler
    (splitter.out_1, normal),    # Explicit: route to normal handler
    (splitter.out_2, low)        # Explicit: route to low priority
])
```

**When to use:**
- Agent has multiple input/output ports
- Need explicit routing
- Want self-documenting code

#### Mixed Syntax
```python
# Can mix simple and explicit
g = network([
    (source, splitter),           # Simple (defaults work)
    (splitter.out_0, sink_a),     # Explicit from side
    (splitter.out_1, sink_b.in_)  # Explicit both sides
])
```

### Algorithm

```python
def network(edges):
    # 1. Parse edges and extract agents
    blocks = {}  # name → agent
    connections = []  # 4-tuples
    
    for (from_node, to_node) in edges:
        # Parse from side
        from_agent, from_port = parse_from(from_node)
        
        # Parse to side
        to_agent, to_port = parse_to(to_node)
        
        # Add to blocks (if not already there)
        if from_agent.name not in blocks:
            blocks[from_agent.name] = from_agent
        if to_agent.name not in blocks:
            blocks[to_agent.name] = to_agent
        
        # Add connection
        connections.append((
            from_agent.name, from_port,
            to_agent.name, to_port
        ))
    
    # 2. Create Network
    return Network(blocks=blocks, connections=connections)
```

### Edge Parsing Details

#### parse_from(node) - Sender Side

```python
def parse_from(node):
    """
    Parse sender (from) side of edge.
    
    Returns: (agent, port_name)
    
    Cases:
    1. PortReference: Use explicit port
    2. Agent with default_outport: Use default
    3. Agent without default: Error (must use explicit)
    4. Network with single outport: Use that port
    5. Network with multiple outports: Error (must use explicit)
    """
    if isinstance(node, PortReference):
        return node.agent, node.port_name
    
    elif isinstance(node, Agent):
        port = node.default_outport
        if port is None:
            raise ValueError(
                f"Agent '{node.name}' has no default outport. "
                f"Use explicit syntax: {node.name}.port_name"
            )
        return node, port
    
    elif isinstance(node, Network):
        if len(node.outports) != 1:
            raise ValueError(
                f"Network '{node.name}' has {len(node.outports)} outports. "
                f"Use explicit syntax: {node.name}.port_name"
            )
        return node, node.outports[0]
    
    else:
        raise TypeError(
            f"Expected Agent, Network, or PortReference, "
            f"got {type(node).__name__}"
        )
```

#### parse_to(node) - Receiver Side

```python
def parse_to(node):
    """
    Parse receiver (to) side of edge.
    
    Returns: (agent, port_name)
    
    Cases: Same as parse_from but uses default_inport
    """
    if isinstance(node, PortReference):
        return node.agent, node.port_name
    
    elif isinstance(node, Agent):
        port = node.default_inport
        if port is None:
            raise ValueError(
                f"Agent '{node.name}' has no default inport. "
                f"Use explicit syntax: {node.name}.port_name"
            )
        return node, port
    
    elif isinstance(node, Network):
        if len(node.inports) != 1:
            raise ValueError(
                f"Network '{node.name}' has {len(node.inports)} inports. "
                f"Use explicit syntax: {node.name}.port_name"
            )
        return node, node.inports[0]
    
    else:
        raise TypeError(
            f"Expected Agent, Network, or PortReference, "
            f"got {type(node).__name__}"
        )
```

---

## PortReference Class

### Purpose
Represent explicit port references for dot notation syntax.

### Implementation

```python
class PortReference:
    """
    Explicit reference to an agent's port.
    
    Created automatically when accessing agent.port_name
    Used in edge specifications for explicit routing.
    """
    
    def __init__(self, agent: Agent | Network, port_name: str):
        """
        Create a PortReference.
        
        Args:
            agent: The Agent or Network instance
            port_name: Name of the port
        
        Note: Typically created via agent.__getattr__, not directly
        """
        self.agent = agent
        self.port_name = port_name
    
    def __repr__(self):
        return f"PortReference({self.agent.name}.{self.port_name})"
    
    def __str__(self):
        return f"{self.agent.name}.{self.port_name}"
```

### Creation via __getattr__

PortReferences are created automatically by Agent's `__getattr__`:

```python
# In Agent class:
def __getattr__(self, name: str):
    """Enable dot notation for ports."""
    if name in self.inports or name in self.outports:
        return PortReference(agent=self, port_name=name)
    
    raise AttributeError(
        f"'{type(self).__name__}' has no attribute '{name}'. "
        f"Valid ports: inports={self.inports}, outports={self.outports}"
    )
```

### Usage Examples

```python
# Create agent with multiple outputs
splitter = Split(num_outputs=3, name="classifier")

# Access ports - creates PortReferences automatically
splitter.out_0  # → PortReference(classifier.out_0)
splitter.out_1  # → PortReference(classifier.out_1)
splitter.out_2  # → PortReference(classifier.out_2)

# Use in edges
g = network([
    (source, splitter),
    (splitter.out_0, urgent_handler),  # PortReference used here
    (splitter.out_1, normal_handler),
    (splitter.out_2, low_handler)
])
```

### Error Handling

```python
# Invalid port
splitter.out_5  # AttributeError: 'Split' has no attribute 'out_5'
                # Valid ports: inports=['in_'], outports=['out_0', 'out_1', 'out_2']

# Typo
splitter.output_0  # AttributeError: 'Split' has no attribute 'output_0'
```

---

## Default Port Strategy

### Philosophy

**Simple case should be simple:**
- 90% of edges: single input/output → use defaults
- 10% of edges: multiple ports → require explicit

### Agent Default Ports

#### Source (no inputs, single output)
```python
class Source(Agent):
    @property
    def default_outport(self):
        return "out_"  # Always "out_"
    
    @property
    def default_inport(self):
        return None  # No inputs
```

#### Transform (single input, single output)
```python
class Transform(Agent):
    @property
    def default_inport(self):
        return "in_"  # Always "in_"
    
    @property
    def default_outport(self):
        return "out_"  # Always "out_"
```

#### Sink (single input, no outputs)
```python
class Sink(Agent):
    @property
    def default_inport(self):
        return "in_"  # Always "in_"
    
    @property
    def default_outport(self):
        return None  # No outputs
```

#### Split (single input, multiple outputs)
```python
class Split(Agent):
    @property
    def default_inport(self):
        return "in_"  # Single input
    
    @property
    def default_outport(self):
        return None  # Ambiguous - must be explicit
```

#### Merge (multiple inputs, single output)
```python
class MergeAsynch(Agent):
    @property
    def default_inport(self):
        return None  # Ambiguous - must be explicit
    
    @property
    def default_outport(self):
        return "out_"  # Single output
```

### Network Default Ports

```python
# Component with single external port - can use default
component = Network(
    inports=["in_"],
    outports=["out_"],
    ...
)

g = network([
    (source, component),  # ✓ Works: component has single inport
    (component, sink)     # ✓ Works: component has single outport
])

# Component with multiple ports - must be explicit
multi_component = Network(
    inports=["data_in", "config_in"],
    outports=["results", "errors"],
    ...
)

g = network([
    (data_source, multi_component.data_in),      # ✓ Explicit required
    (config_source, multi_component.config_in),  # ✓ Explicit required
    (multi_component.results, results_sink),     # ✓ Explicit required
    (multi_component.errors, error_handler)      # ✓ Explicit required
])
```

---

## Name Validation

### Requirement: Unique Names

All agents must have unique names:

```python
# ✓ Valid - all names unique
source = Source(fn=gen, name="twitter")
transform = Transform(fn=clean, name="cleaner")
sink = Sink(fn=save, name="database")

# ✗ Invalid - duplicate name
source_a = Source(fn=gen_a, name="source")
source_b = Source(fn=gen_b, name="source")  # Same name!

g = network([
    (source_a, sink),
    (source_b, sink)
])
# ValueError: Duplicate agent name 'source'
```

### Checking

```python
def network(edges):
    blocks = {}
    
    for (from_node, to_node) in edges:
        from_agent, _ = parse_from(from_node)
        to_agent, _ = parse_to(to_node)
        
        # Check for duplicates
        for agent in [from_agent, to_agent]:
            if agent.name in blocks and blocks[agent.name] is not agent:
                raise ValueError(
                    f"Duplicate agent name '{agent.name}'. "
                    f"Each agent must have a unique name."
                )
            blocks[agent.name] = agent
    
    return Network(blocks=blocks, connections=...)
```

### Best Practice

Use descriptive, unique names:
```python
# Good names (self-documenting)
twitter_feed = Source(fn=..., name="twitter_feed")
reddit_feed = Source(fn=..., name="reddit_feed")
text_cleaner = Transform(fn=..., name="text_cleaner")
sentiment_analyzer = Transform(fn=..., name="sentiment_analyzer")

# Bad names (ambiguous)
source_1 = Source(fn=..., name="source_1")  # What source?
source_2 = Source(fn=..., name="source_2")  # What source?
transform_1 = Transform(fn=..., name="transform_1")  # What does it do?
```

---

## Error Messages

### Philosophy

Error messages should:
1. Explain what's wrong
2. Show where it happened
3. Suggest how to fix it

### Examples

#### No Default Port

```python
splitter = Split(num_outputs=3, name="classifier")

g = network([
    (source, splitter),
    (splitter, handler)  # Error: which output?
])
```

**Error:**
```
ValueError: Agent 'classifier' has no default outport.

The agent has multiple output ports:
  - out_0
  - out_1
  - out_2

Use explicit syntax to specify which port:
  (splitter.out_0, handler)
  (splitter.out_1, handler)
  (splitter.out_2, handler)
```

#### Invalid Port Reference

```python
splitter.out_5  # Port doesn't exist
```

**Error:**
```
AttributeError: 'Split' object has no attribute 'out_5'

Valid ports for agent 'classifier':
  Inports:  ['in_']
  Outports: ['out_0', 'out_1', 'out_2']

Did you mean one of these?
  classifier.out_0
  classifier.out_1
  classifier.out_2
```

#### Duplicate Names

```python
src_a = Source(fn=..., name="src")
src_b = Source(fn=..., name="src")  # Duplicate!
```

**Error:**
```
ValueError: Duplicate agent name 'src'

Two different agents have the same name:
  - Source at 0x7f8b4c
  - Source at 0x7f8b5d

Each agent must have a unique name. Consider:
  src_a = Source(fn=..., name="twitter_feed")
  src_b = Source(fn=..., name="reddit_feed")
```

---

## Design Rationale

### Why 2-Tuple Edges?

**Alternatives:**
```python
# Option A: 4-tuples (explicit everything)
(("source", "out_"), ("transform", "in_"))

# Option B: Edge objects
Edge(from_agent=source, to_agent=transform)

# Option C: Builder methods
network.add_edge(source, transform)
```

**Chosen: 2-tuples with smart parsing**
```python
(source, transform)  # Simple
(splitter.out_0, handler)  # Explicit when needed
```

**Rationale:**
- Natural syntax (looks like math notation)
- Simple case is simple (no boilerplate)
- Complex case is explicit (dot notation)
- Compact (easy to read)
- Type-checkable (with proper annotations)

### Why PortReference vs String Ports?

**Alternative: String-based**
```python
network([
    (source, "out_", transform, "in_")  # 4-tuple always
])
```

**Chosen: PortReference with dot notation**
```python
network([
    (source, transform),      # Simple
    (splitter.out_0, handler)  # Explicit
])
```

**Rationale:**
- Dot notation is Python idiomatic
- Type-safe (catches typos at parse time)
- IDE support (autocomplete for ports)
- Self-documenting (port name at use site)

### Why Default Ports?

**Alternative: Always explicit**
```python
network([
    (source.out_, transform.in_),  # Always specify ports
    (transform.out_, sink.in_)
])
```

**Chosen: Defaults with override**
```python
network([
    (source, transform),  # Use defaults
    (transform, sink)
])
```

**Rationale:**
- 90% of edges are simple (single in/out)
- Reduces boilerplate and visual noise
- Still explicit when needed (complex cases)
- Teaches pattern (simple default, explicit override)

---

## Usage Patterns

### Linear Pipeline

```python
# Simplest case: chain of transforms
g = network([
    (source, clean),
    (clean, analyze),
    (analyze, format),
    (format, sink)
])
```

### Fanout (Broadcast)

```python
# One source, multiple consumers
g = network([
    (source, transform_a),
    (source, transform_b),
    (source, transform_c)
])
# Broadcast inserted automatically
```

### Fanin (Merge)

```python
# Multiple sources, one consumer
g = network([
    (source_a, processor),
    (source_b, processor),
    (source_c, processor)
])
# Merge inserted automatically
```

### Explicit Routing

```python
# Classify and route to different handlers
splitter = Split(router=classify, num_outputs=3, name="classifier")

g = network([
    (source, splitter),
    (splitter.out_0, urgent_handler),
    (splitter.out_1, normal_handler),
    (splitter.out_2, low_handler)
])
```

### Component Composition

```python
# Use tested components as building blocks
component_a = inner_a.as_component(...)
component_b = inner_b.as_component(...)

g = network([
    (source, component_a),
    (component_a, component_b),
    (component_b, sink)
])
```

---

## Testing

### Unit Tests

```python
def test_simple_edge_parsing():
    """Test parsing simple edges."""
    source = Source(fn=gen, name="src")
    sink = Sink(fn=save, name="sink")
    
    g = network([(source, sink)])
    
    assert "src" in g.blocks
    assert "sink" in g.blocks
    assert g.connections == [("src", "out_", "sink", "in_")]


def test_explicit_port_parsing():
    """Test parsing explicit port references."""
    split = Split(num_outputs=2, name="split")
    sink_a = Sink(fn=save_a, name="sink_a")
    sink_b = Sink(fn=save_b, name="sink_b")
    
    g = network([
        (source, split),
        (split.out_0, sink_a),
        (split.out_1, sink_b)
    ])
    
    assert g.connections == [
        ("source", "out_", "split", "in_"),
        ("split", "out_0", "sink_a", "in_"),
        ("split", "out_1", "sink_b", "in_")
    ]


def test_duplicate_name_error():
    """Test error on duplicate names."""
    src_a = Source(fn=gen, name="src")
    src_b = Source(fn=gen, name="src")  # Duplicate!
    
    with pytest.raises(ValueError, match="Duplicate agent name"):
        network([(src_a, sink), (src_b, sink)])
```

### Integration Tests

```python
def test_network_execution():
    """Test complete network execution."""
    results = []
    
    source = Source(fn=lambda: [1, 2, 3], name="src")
    double = Transform(fn=lambda x: x * 2, name="dbl")
    sink = Sink(fn=results.append, name="sink")
    
    g = network([
        (source, double),
        (double, sink)
    ])
    g.run_network()
    
    assert results == [2, 4, 6]
```