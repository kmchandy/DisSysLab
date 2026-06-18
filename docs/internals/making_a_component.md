# Understanding `as_component`: Converting Graphs to Reusable Network Components

## Overview

The `as_component` function transforms a flat graph into a hierarchical Network component with explicit external input/output ports. This enables compositional design where students can build small, tested components and combine them into larger systems.

## Function Signature

```python
def as_component(graph, inports=None, outports=None):
    """
    Convert a graph into a reusable Network component.
    
    Args:
        graph: An existing network/graph to wrap as a component
        inports: List of (external_name, node_or_port) tuples defining inputs
        outports: List of (external_name, node_or_port) tuples defining outputs
    
    Returns:
        Network: A Network object with external ports that can be nested in other networks
    """
```

## Example Walkthrough

### Initial Setup

We have an inner network with test sources and sinks that we want to convert into a reusable component:

```python
inner = network([
    (test_source_1, A),
    (test_source_1, B),
    (test_source_2, C),
    # ... (other internal connections)
    (X, test_sink_1),
    (Y, test_sink_1),
    (Z, test_sink_2)
])
```

We call `as_component` to create a reusable component:

```python
component = as_component(
    inner,
    inports=[("in_1", test_source_1), ("in_2", test_source_2)],
    outports=[("out_1", test_sink_1), ("out_2", test_sink_2)]
)
```

---

## Step-by-Step Execution

### Step 1: Parse inports to 4-tuples

**Input:**
```python
inports = [("in_1", test_source_1), ("in_2", test_source_2)]
```

**Processing:**
```python
# For ("in_1", test_source_1):
agent = test_source_1
port = "out_"  # (assuming default outport)
agent_name = "test_source_1"
→ ("external", "in_1", "test_source_1", "out_")

# For ("in_2", test_source_2):
→ ("external", "in_2", "test_source_2", "out_")
```

**Result:**
```python
parsed_inports = [
    ("external", "in_1", "test_source_1", "out_"),
    ("external", "in_2", "test_source_2", "out_")
]
```

**Explanation:** This standardizes external inputs into connection format. It says "data coming from outside on port `in_1` should connect to `test_source_1.out_`"

---

### Step 2: Parse outports to 4-tuples

**Input:**
```python
outports = [("out_1", test_sink_1), ("out_2", test_sink_2)]
```

**Processing:**
```python
# For ("out_1", test_sink_1):
agent = test_sink_1
port = "in_"  # (assuming default inport)
agent_name = "test_sink_1"
→ ("test_sink_1", "in_", "external", "out_1")

# For ("out_2", test_sink_2):
→ ("test_sink_2", "in_", "external", "out_2")
```

**Result:**
```python
parsed_outports = [
    ("test_sink_1", "in_", "external", "out_1"),
    ("test_sink_2", "in_", "external", "out_2")
]
```

**Explanation:** This standardizes external outputs. It says "data from `test_sink_1.in_` should go out through external port `out_1`"

---

### Steps 3 & 4: Replace edges

**Original edges:**
```python
new_edges = [
    ("test_source_1", "out_", "A", "in_"),
    ("test_source_1", "out_", "B", "in_"),
    ("test_source_2", "out_", "C", "in_"),
    # ... other internal edges ...
    ("X", "out_", "test_sink_1", "in_"),
    ("Y", "out_", "test_sink_1", "in_"),
    ("Z", "out_", "test_sink_2", "in_")
]
agents_to_remove = set()
```

#### Processing inports:

**For** `("external", "in_1", "test_source_1", "out_")`:
- Find edges where `fn == "test_source_1"` and `fp == "out_"`
- Replace source side with `("external", "in_1")`

```python
("test_source_1", "out_", "A", "in_") → ("external", "in_1", "A", "in_")
("test_source_1", "out_", "B", "in_") → ("external", "in_1", "B", "in_")
agents_to_remove.add("test_source_1")
```

**For** `("external", "in_2", "test_source_2", "out_")`:
```python
("test_source_2", "out_", "C", "in_") → ("external", "in_2", "C", "in_")
agents_to_remove.add("test_source_2")
```

#### Processing outports:

**For** `("test_sink_1", "in_", "external", "out_1")`:
- Find edges where `tn == "test_sink_1"` and `tp == "in_"`
- Replace destination side with `("external", "out_1")`

```python
("X", "out_", "test_sink_1", "in_") → ("X", "out_", "external", "out_1")
("Y", "out_", "test_sink_1", "in_") → ("Y", "out_", "external", "out_1")
agents_to_remove.add("test_sink_1")
```

**For** `("test_sink_2", "in_", "external", "out_2")`:
```python
("Z", "out_", "test_sink_2", "in_") → ("Z", "out_", "external", "out_2")
agents_to_remove.add("test_sink_2")
```

#### Result after edge replacement:

```python
new_edges = [
    ("external", "in_1", "A", "in_"),
    ("external", "in_1", "B", "in_"),
    ("external", "in_2", "C", "in_"),
    # ... other internal edges ...
    ("X", "out_", "external", "out_1"),
    ("Y", "out_", "external", "out_1"),
    ("Z", "out_", "external", "out_2")
]

agents_to_remove = {
    "test_source_1", 
    "test_source_2", 
    "test_sink_1", 
    "test_sink_2"
}
```

**Explanation:** This "splices out" the boundary agents. External connections now reference "external" as a block name. The removed agents were just interface points and no longer serve a purpose inside the component.

---

### Step 5: Build blocks dict

```python
# Original blocks in inner network:
# {A, B, C, ..., X, Y, Z, test_source_1, test_source_2, test_sink_1, test_sink_2}

new_blocks = {
    "A": A,
    "B": B,
    "C": C,
    # ... other internal agents ...
    "X": X,
    "Y": Y,
    "Z": Z
    # test_source_1, test_source_2, test_sink_1, test_sink_2 are REMOVED
}
```

**Explanation:** Removes agents that were replaced by external connections. These were just interface placeholders—data now comes from/goes to the outside instead.

---

### Step 6: Extract external port names

```python
inport_names = ["in_1", "in_2"]
outport_names = ["out_1", "out_2"]
```

**Explanation:** Network's constructor needs simple lists of port names, not the full connection tuples.

---

### Step 7: Create and return Network

```python
component = Network(
    blocks=new_blocks,      # A, B, C, ..., X, Y, Z (no test sources/sinks)
    connections=new_edges,  # edges with "external" references
    inports=["in_1", "in_2"],
    outports=["out_1", "out_2"]
)
```

**Explanation:** Creates a reusable component with well-defined external interfaces that can be nested in other networks.

---

## Using the Component in an Outer Network

Now we can use our component as a building block:

```python
outer = network([
    (agent_1, component.in_1),  # agent_1.port_1 → component.in_1
    (agent_2, component.in_1),  # agent_2.port_2 → component.in_1
    (agent_3, component.in_2),  # agent_3.port_3 → component.in_2
    (component.out_1, agent_4), # component.out_1 → agent_4.port_4
    (component.out_1, agent_5), # component.out_1 → agent_5.port_5
    (component.out_2, agent_6)  # component.out_2 → agent_6.port_6
])
```

**Initial outer edges (before flattening):**
```python
[
    ("agent_1", "port_1", "component", "in_1"),
    ("agent_2", "port_2", "component", "in_1"),
    ("agent_3", "port_3", "component", "in_2"),
    ("component", "out_1", "agent_4", "port_4"),
    ("component", "out_1", "agent_5", "port_5"),
    ("component", "out_2", "agent_6", "port_6")
]
```

---

## Network Compilation and Flattening

When `outer.compile()` runs, it flattens nested networks through a multi-step process:

### Component's Internal Connections

After `as_component` transformed them:
```python
[
    ("external", "in_1", "A", "in_"),
    ("external", "in_1", "B", "in_"),
    ("external", "in_2", "C", "in_"),
    # ... internal edges ...
    ("X", "out_", "external", "out_1"),
    ("Y", "out_", "external", "out_1"),
    ("Z", "out_", "external", "out_2")
]
```

### Lifting (Adding Path Prefix)

All component blocks get prefixed with "component.":
```python
[
    ("component", "in_1", "component.A", "in_"),      # external.in_1 → component.in_1
    ("component", "in_1", "component.B", "in_"),
    ("component", "in_2", "component.C", "in_"),
    # ... internal edges ...
    ("component.X", "out_", "component", "out_1"),
    ("component.Y", "out_", "component", "out_1"),
    ("component.Z", "out_", "component", "out_2")
]
```

### Resolving External Connections (Fixpoint Iteration)

The compiler collapses chains of connections through "external" boundaries:

**Inport resolutions:**

```python
("agent_1", "port_1", "component", "in_1") + ("component", "in_1", "component.A", "in_")
→ ("agent_1", "port_1", "component.A", "in_")

("agent_2", "port_2", "component", "in_1") + ("component", "in_1", "component.B", "in_")
→ ("agent_2", "port_2", "component.B", "in_")

("agent_3", "port_3", "component", "in_2") + ("component", "in_2", "component.C", "in_")
→ ("agent_3", "port_3", "component.C", "in_")
```

**Outport resolutions:**

```python
("component.X", "out_", "component", "out_1") + ("component", "out_1", "agent_4", "port_4")
→ ("component.X", "out_", "agent_4", "port_4")

("component.Y", "out_", "component", "out_1") + ("component", "out_1", "agent_5", "port_5")
→ ("component.Y", "out_", "agent_5", "port_5")

("component.Z", "out_", "component", "out_2") + ("component", "out_2", "agent_6", "port_6")
→ ("component.Z", "out_", "agent_6", "port_6")
```

---

## Final Flattened Network

After complete compilation, all component boundaries are resolved into direct agent-to-agent connections:

```python
[
    # External agents connecting to component internals
    ("agent_1", "port_1", "component.A", "in_"),
    ("agent_2", "port_2", "component.B", "in_"),
    ("agent_3", "port_3", "component.C", "in_"),
    
    # ... other internal component edges (unchanged) ...
    
    # Component internals connecting to external agents
    ("component.X", "out_", "agent_4", "port_4"),
    ("component.Y", "out_", "agent_5", "port_5"),
    ("component.Z", "out_", "agent_6", "port_6")
]
```

**Key insight:** The component boundary (`component.in_1`, `component.out_1`, etc.) completely disappears during compilation. We're left with direct connections between the outer network's agents and the component's internal agents.

---

## Summary

The `as_component` function enables compositional design by:

1. **Identifying boundaries**: Parsing which agents form the external interface
2. **Rewiring connections**: Replacing boundary agents with "external" pseudo-block references
3. **Removing scaffolding**: Deleting agents that only served as interface points
4. **Packaging**: Creating a Network with explicit external ports

During network compilation, these external references are resolved through fixpoint iteration, ultimately creating direct agent-to-agent connections. This allows students to:

- Build small, testable components
- Combine components into larger systems
- Understand distributed systems architecture through composition
- Reuse components across different projects

The test sources and sinks are completely removed from the final component, making it a clean, reusable building block with well-defined inputs and outputs.