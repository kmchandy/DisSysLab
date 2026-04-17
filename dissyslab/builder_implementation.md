# builder.py - Implementation Guide

## File Purpose

`dsl/builder.py` provides the user-facing API for building networks:
- `network()` function: Main entry point for creating networks from edge lists
- `PortReference` class: Enables dot notation for explicit port specification

**Core Responsibilities:**
1. Parse edge list with four possible patterns
2. Extract agents from edges
3. Validate agent names are unique
4. Create Network instance with proper structure
5. Enable `agent.port_name` syntax via `__getattr__`

## What Goes in builder.py

**Include:**
- `PortReference` class
- `network()` function
- Helper functions for parsing edges

**Do NOT include:**
- `Agent` class (in `core.py`)
- `Network` class (in `network.py`)
- Concrete agent types (in `blocks/`)

---

## Dependencies

```python
from __future__ import annotations
from typing import List, Tuple, Union, TYPE_CHECKING

if TYPE_CHECKING:
    from dsl.core import Agent

# Actual imports
from dsl.network import Network
```

**Note:** We use `TYPE_CHECKING` to avoid circular import issues since Agent.__getattr__ imports PortReference.

---

## PortReference Class

### Purpose

Enable dot notation for explicit port specification:
```python
source.out_     # Creates PortReference(agent=source, port_name="out_")
transform.in_   # Creates PortReference(agent=transform, port_name="in_")
```

### Implementation

```python
class PortReference:
    """
    Reference to a specific port on an agent.
    
    Created automatically when accessing agent.port_name via __getattr__.
    Used in network() edges to specify explicit ports.
    
    Example:
        >>> source.out_
        PortReference(agent=source, port_name="out_")
        
        >>> network([(source.out_, transform.in_)])
        # Uses PortReference to specify exact ports
    
    Attributes:
        agent: The agent this port belongs to
        port_name: Name of the port (e.g., "out_", "in_", "out_0")
    """
    
    def __init__(self, agent: Agent, port_name: str):
        """
        Initialize PortReference.
        
        Args:
            agent: Agent instance that owns this port
            port_name: Name of the port on the agent
        
        Note:
            Usually created automatically via agent.__getattr__,
            not instantiated directly by users.
        """
        self.agent = agent
        self.port_name = port_name
    
    def __repr__(self) -> str:
        """
        Readable representation for debugging.
        
        Returns:
            String like "PortReference(agent_name.port_name)"
        """
        agent_name = self.agent.name if self.agent.name else "<unnamed>"
        return f"PortReference({agent_name}.{self.port_name})"
    
    def __str__(self) -> str:
        """
        String representation using dot notation.
        
        Returns:
            String like "agent_name.port_name"
        """
        agent_name = self.agent.name if self.agent.name else "<unnamed>"
        return f"{agent_name}.{self.port_name}"
```

**Requirements:**
- ✅ Simple data class with two attributes
- ✅ Created by Agent.__getattr__ (not directly by users)
- ✅ Readable repr for debugging
- ✅ String representation uses dot notation

---

## network() Function

### Purpose

Build Network from edge list using natural syntax:
```python
g = network([
    (source, transform),          # Pattern 1: both defaults
    (source.out_, transform),     # Pattern 2: explicit from, default to
    (source, transform.in_),      # Pattern 3: default from, explicit to
    (source.out_, transform.in_)  # Pattern 4: both explicit
])
```

### Function Signature

```python
def network(
    edges: List[Tuple[Union['Agent', PortReference], Union['Agent', PortReference]]]
) -> Network:
    """
    Build a Network from edge list.
    
    Each edge is a 2-tuple connecting two nodes. Nodes can be:
    - Agent instance: Uses agent's default port
    - PortReference: Uses explicit port (agent.port_name)
    
    Four edge patterns:
    1. (agent, agent): Both use default ports
    2. (agent.port, agent): Explicit from, default to
    3. (agent, agent.port): Default from, explicit to
    4. (agent.port, agent.port): Both explicit
    
    Args:
        edges: List of 2-tuples (from_node, to_node)
    
    Returns:
        Network instance ready to compile and run
    
    Raises:
        TypeError: If edges is not a list
        TypeError: If edge is not a 2-tuple
        TypeError: If edge nodes are not Agent or PortReference
        ValueError: If agent has no default port when needed
        ValueError: If agent names are not unique
        ValueError: If port doesn't exist on agent
    
    Example:
        >>> source = Source(fn=generate, name="src")
        >>> transform = Transform(fn=process, name="trans")
        >>> sink = Sink(fn=save, name="sink")
        >>> 
        >>> g = network([
        ...     (source, transform),
        ...     (transform, sink)
        ... ])
        >>> g.run_network()
    """
```

### Main Implementation

```python
def network(edges):
    """Build Network from edge list."""
    
    # Step 1: Validate input type
    if not isinstance(edges, list):
        raise TypeError(
            f"edges must be a list, got {type(edges).__name__}\n\n"
            f"Example:\n"
            f"  g = network([\n"
            f"      (source, transform),\n"
            f"      (transform, sink)\n"
            f"  ])"
        )
    
    # Step 2: Parse edges and collect agents
    blocks = {}  # name → agent
    connections = []  # 4-tuples
    
    for i, edge in enumerate(edges):
        # Validate edge structure
        if not isinstance(edge, tuple) or len(edge) != 2:
            edge_type = type(edge).__name__
            edge_len = len(edge) if isinstance(edge, tuple) else "N/A"
            raise TypeError(
                f"Edge {i} must be a 2-tuple, got {edge_type} with {edge_len} elements\n\n"
                f"Expected format:\n"
                f"  (source, transform)              # Both agents\n"
                f"  (source.out_, transform.in_)     # Both PortReferences\n"
                f"  (source.out_, transform)         # Mixed\n\n"
                f"Got: {edge}"
            )
        
        from_node, to_node = edge
        
        # Parse from side
        from_agent, from_port = _parse_from_node(from_node, i)
        
        # Parse to side
        to_agent, to_port = _parse_to_node(to_node, i)
        
        # Add agents to blocks dict (check for duplicates)
        _add_agent_to_blocks(blocks, from_agent)
        _add_agent_to_blocks(blocks, to_agent)
        
        # Create 4-tuple connection
        connections.append((
            from_agent.name,
            from_port,
            to_agent.name,
            to_port
        ))
    
    # Step 3: Create and return Network
    return Network(blocks=blocks, connections=connections)
```

### Helper Functions

#### _parse_from_node()

```python
def _parse_from_node(node, edge_index: int) -> Tuple['Agent', str]:
    """
    Parse from-node of an edge.
    
    Args:
        node: Agent or PortReference
        edge_index: Index of edge (for error messages)
    
    Returns:
        (agent, port_name) tuple
    
    Raises:
        TypeError: If node is not Agent or PortReference
        ValueError: If Agent has no default outport
        ValueError: If port doesn't exist on agent
    """
    from dsl.core import Agent
    
    # Case 1: PortReference (explicit port)
    if isinstance(node, PortReference):
        agent = node.agent
        port = node.port_name
        
        # Validate port exists
        if port not in agent.outports:
            raise ValueError(
                f"Edge {edge_index}: Port '{port}' is not a valid outport of agent '{agent.name}'.\n"
                f"Valid outports: {agent.outports}\n\n"
                f"Did you mean one of these?\n" +
                "\n".join(f"  {agent.name}.{p}" for p in agent.outports)
            )
        
        return agent, port
    
    # Case 2: Agent (use default port)
    elif isinstance(node, Agent):
        agent = node
        port = agent.default_outport
        
        if port is None:
            raise ValueError(
                f"Edge {edge_index}: Agent '{agent.name}' has no default outport.\n"
                f"The agent has these outports: {agent.outports}\n\n"
                f"Use explicit port syntax:\n" +
                "\n".join(f"  ({agent.name}.{p}, ...)") for p in agent.outports) +
                f"\n\nExample:\n"
                f"  ({agent.name}.{agent.outports[0] if agent.outports else 'port_name'}, next_agent)"
            )
        
        return agent, port
    
    # Case 3: Invalid type
    else:
        raise TypeError(
            f"Edge {edge_index}: from-node must be Agent or PortReference, "
            f"got {type(node).__name__}\n\n"
            f"Expected:\n"
            f"  (agent, ...)              # Agent instance\n"
            f"  (agent.port_name, ...)    # PortReference\n\n"
            f"Got: {node}"
        )
```

#### _parse_to_node()

```python
def _parse_to_node(node, edge_index: int) -> Tuple['Agent', str]:
    """
    Parse to-node of an edge.
    
    Args:
        node: Agent or PortReference
        edge_index: Index of edge (for error messages)
    
    Returns:
        (agent, port_name) tuple
    
    Raises:
        TypeError: If node is not Agent or PortReference
        ValueError: If Agent has no default inport
        ValueError: If port doesn't exist on agent
    """
    from dsl.core import Agent
    
    # Case 1: PortReference (explicit port)
    if isinstance(node, PortReference):
        agent = node.agent
        port = node.port_name
        
        # Validate port exists
        if port not in agent.inports:
            raise ValueError(
                f"Edge {edge_index}: Port '{port}' is not a valid inport of agent '{agent.name}'.\n"
                f"Valid inports: {agent.inports}\n\n"
                f"Did you mean one of these?\n" +
                "\n".join(f"  {agent.name}.{p}" for p in agent.inports)
            )
        
        return agent, port
    
    # Case 2: Agent (use default port)
    elif isinstance(node, Agent):
        agent = node
        port = agent.default_inport
        
        if port is None:
            raise ValueError(
                f"Edge {edge_index}: Agent '{agent.name}' has no default inport.\n"
                f"The agent has these inports: {agent.inports}\n\n"
                f"Use explicit port syntax:\n" +
                "\n".join(f"  (..., {agent.name}.{p})" for p in agent.inports) +
                f"\n\nExample:\n"
                f"  (prev_agent, {agent.name}.{agent.inports[0] if agent.inports else 'port_name'})"
            )
        
        return agent, port
    
    # Case 3: Invalid type
    else:
        raise TypeError(
            f"Edge {edge_index}: to-node must be Agent or PortReference, "
            f"got {type(node).__name__}\n\n"
            f"Expected:\n"
            f"  (..., agent)              # Agent instance\n"
            f"  (..., agent.port_name)    # PortReference\n\n"
            f"Got: {node}"
        )
```

#### _add_agent_to_blocks()

```python
def _add_agent_to_blocks(blocks: Dict[str, 'Agent'], agent: 'Agent') -> None:
    """
    Add agent to blocks dictionary with duplicate checking.
    
    Args:
        blocks: Dictionary mapping names to agents
        agent: Agent to add
    
    Raises:
        ValueError: If agent name already exists with different instance
    """
    if agent.name not in blocks:
        blocks[agent.name] = agent
    elif blocks[agent.name] is not agent:
        raise ValueError(
            f"Duplicate agent name: '{agent.name}'\n\n"
            f"Two different agent instances have the same name.\n"
            f"Each agent must have a unique name.\n\n"
            f"Solution: Give agents different names:\n"
            f"  source_a = Source(fn=gen_a, name='src_a')\n"
            f"  source_b = Source(fn=gen_b, name='src_b')\n"
        )
```

---

## Error Message Philosophy

### Principle: Help Students Fix the Problem

Every error message should include:
1. **What went wrong** (clear description)
2. **Why it's wrong** (explanation)
3. **How to fix it** (concrete examples)

### Examples

**Good error message:**
```
Edge 2: Agent 'splitter' has no default outport.
The agent has these outports: ['out_0', 'out_1', 'out_2']

Use explicit port syntax:
  (splitter.out_0, ...)
  (splitter.out_1, ...)
  (splitter.out_2, ...)

Example:
  (splitter.out_0, next_agent)
```

**Bad error message:**
```
ValueError: No default outport
```

---

## Testing Strategy

### Unit Tests for PortReference

```python
def test_portreference_creation():
    """PortReference stores agent and port name."""
    agent = Source(fn=lambda: [1], name="src")
    ref = PortReference(agent=agent, port_name="out_")
    
    assert ref.agent is agent
    assert ref.port_name == "out_"


def test_portreference_repr():
    """PortReference has readable repr."""
    agent = Source(fn=lambda: [1], name="src")
    ref = PortReference(agent=agent, port_name="out_")
    
    assert "src" in repr(ref)
    assert "out_" in repr(ref)


def test_portreference_str():
    """PortReference string uses dot notation."""
    agent = Source(fn=lambda: [1], name="src")
    ref = PortReference(agent=agent, port_name="out_")
    
    assert str(ref) == "src.out_"
```

### Unit Tests for network()

```python
def test_network_simple_pipeline():
    """Test simple source → transform → sink pipeline."""
    source = Source(fn=lambda: [1], name="src")
    transform = Transform(fn=lambda x: x * 2, name="trans")
    sink = Sink(fn=lambda x: None, name="sink")
    
    g = network([
        (source, transform),
        (transform, sink)
    ])
    
    assert "src" in g.blocks
    assert "trans" in g.blocks
    assert "sink" in g.blocks
    assert len(g.connections) == 2
    assert g.connections[0] == ("src", "out_", "trans", "in_")
    assert g.connections[1] == ("trans", "out_", "sink", "in_")


def test_network_explicit_ports():
    """Test using explicit port syntax."""
    source = Source(fn=lambda: [1], name="src")
    transform = Transform(fn=lambda x: x, name="trans")
    
    g = network([
        (source.out_, transform.in_)
    ])
    
    assert g.connections == [("src", "out_", "trans", "in_")]


def test_network_mixed_syntax():
    """Test mixing default and explicit ports."""
    source = Source(fn=lambda: [1], name="src")
    splitter = Split(num_outputs=2, name="split")
    sink = Sink(fn=lambda x: None, name="sink")
    
    g = network([
        (source, splitter),              # Both defaults
        (splitter.out_0, sink)           # Explicit from, default to
    ])
    
    assert g.connections[0] == ("src", "out_", "split", "in_")
    assert g.connections[1] == ("split", "out_0", "sink", "in_")


def test_network_duplicate_name_error():
    """Test error on duplicate agent names."""
    src_a = Source(fn=lambda: [1], name="src")
    src_b = Source(fn=lambda: [2], name="src")  # Same name!
    
    with pytest.raises(ValueError, match="Duplicate agent name"):
        network([(src_a, src_b)])


def test_network_no_default_outport_error():
    """Test error when agent has no default outport."""
    source = Source(fn=lambda: [1], name="src")
    splitter = Split(num_outputs=2, name="split")
    
    with pytest.raises(ValueError, match="no default outport"):
        network([(splitter, source)])  # Splitter has no default outport


def test_network_invalid_port_error():
    """Test error when port doesn't exist."""
    source = Source(fn=lambda: [1], name="src")
    transform = Transform(fn=lambda x: x, name="trans")
    
    # Create invalid PortReference manually
    bad_ref = PortReference(agent=source, port_name="invalid")
    
    with pytest.raises(ValueError, match="not a valid outport"):
        network([(bad_ref, transform)])


def test_network_wrong_type_error():
    """Test error when edge node is wrong type."""
    source = Source(fn=lambda: [1], name="src")
    
    with pytest.raises(TypeError, match="must be Agent or PortReference"):
        network([("string", source)])


def test_network_wrong_edge_structure():
    """Test error when edge is not 2-tuple."""
    source = Source(fn=lambda: [1], name="src")
    transform = Transform(fn=lambda x: x, name="trans")
    
    with pytest.raises(TypeError, match="must be a 2-tuple"):
        network([(source, transform, "extra")])


def test_network_edges_not_list():
    """Test error when edges is not a list."""
    with pytest.raises(TypeError, match="must be a list"):
        network("not a list")
```

### Integration Tests

```python
def test_network_full_execution():
    """Test complete network construction and execution."""
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


def test_network_fanout():
    """Test fanout pattern (one source, multiple sinks)."""
    results_a = []
    results_b = []
    
    source = Source(fn=lambda: [1, 2], name="src")
    sink_a = Sink(fn=results_a.append, name="sink_a")
    sink_b = Sink(fn=results_b.append, name="sink_b")
    
    g = network([
        (source, sink_a),
        (source, sink_b)
    ])
    
    g.run_network()
    
    # Both sinks should receive all values
    assert results_a == [1, 2]
    assert results_b == [1, 2]


def test_network_complex_routing():
    """Test complex multi-path network."""
    results = []
    
    source = Source(fn=lambda: [1, 2, 3], name="src")
    splitter = Split(router=lambda x: x % 2, num_outputs=2, name="split")
    sink_even = Sink(fn=lambda x: results.append(("even", x)), name="even")
    sink_odd = Sink(fn=lambda x: results.append(("odd", x)), name="odd")
    
    g = network([
        (source, splitter),
        (splitter.out_0, sink_even),
        (splitter.out_1, sink_odd)
    ])
    
    g.run_network()
    
    # Check routing worked
    assert ("even", 2) in results
    assert ("odd", 1) in results
    assert ("odd", 3) in results
```

---

## Common Pitfalls

### 1. Circular Import (Agent ↔ PortReference)

**Problem:** Agent.__getattr__ needs PortReference, PortReference type hints need Agent

**Solution:** 
```python
# In builder.py
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from dsl.core import Agent

# In core.py Agent.__getattr__
def __getattr__(self, name):
    from dsl.builder import PortReference  # Lazy import
    ...
```

### 2. Validating Port Exists

**Problem:** User creates PortReference with invalid port manually

**Solution:** Validate in _parse_from_node and _parse_to_node

### 3. Duplicate Agent Detection

**Problem:** Same agent instance used twice is OK, different instances with same name is not

**Solution:** Check `blocks[name] is not agent` (identity check)

### 4. Error Message Quality

**Problem:** Generic errors don't help students

**Solution:** Include context, explanation, and examples in every error

---

## Implementation Order

1. **PortReference class** - Simple data class
2. **_add_agent_to_blocks()** - Helper for duplicate checking
3. **_parse_from_node()** - Parse from side of edge
4. **_parse_to_node()** - Parse to side of edge
5. **network()** - Main function that orchestrates everything

---

## Ready to Implement?

Once you've reviewed this guide, we can:
1. Write the actual `builder.py` code
2. Write comprehensive tests
3. Verify all four edge patterns work correctly

Any questions or changes before proceeding?