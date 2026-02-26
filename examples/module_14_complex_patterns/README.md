# Module 07: Complex Patterns - Network Topologies for Acyclic Graphs

Learn how to design networks with different topologies. This module covers the fundamental patterns you'll use to build any acyclic network.

## What You'll Learn

- What acyclic networks are and why they matter
- Four fundamental network patterns: fork, join, diamond, general DAG
- How to design network topologies for different problems
- How to think in graphs when building distributed systems
- Why we start with acyclic graphs (cycles come later)

## Understanding Network Topologies

### What is a Network Topology?

A **network topology** is the shape of your network - how nodes connect to each other.

**Key concepts:**
- **Nodes** - Your processing units (Source, Transform, Sink)
- **Edges** - Connections where data flows (`(node_A, node_B)`)
- **Directed** - Edges have direction (A → B, not B → A)
- **Graph** - The complete structure of nodes + edges

### What is an Acyclic Network?

**Acyclic** means "no cycles" - data flows in one direction without loops.
```
✓ Acyclic (allowed):
A → B → C → D

✓ Acyclic (allowed):
    ┌→ B →┐
A ──┤     ├→ D
    └→ C →┘

✗ Cyclic (NOT in this module):
A → B → C → A  (cycle!)
```

**Why start with acyclic?**
- Simpler to understand and debug
- Guaranteed to terminate (no infinite loops)
- Covers 90% of real-world use cases
- Foundation for understanding cycles later

**What about cycles?**
We'll cover cyclic networks (feedback loops, iterative processing) in a later module. For now, focus on acyclic topologies.

---

## The Four Fundamental Patterns

### Pattern 1: Fork (Fanout with Separate Collection)

**Topology:**
```
        ┌→ process_A → sink_A
source ─┤
        └→ process_B → sink_B
```

**Characteristics:**
- One source
- Multiple parallel processors
- Each processor has its own sink
- Paths do NOT merge back together

**When to use:**
- Process same data in multiple different ways
- Want results organized separately by type
- Maximum parallelism with independent outputs

**Example:** Process images to create thumbnails AND extract metadata simultaneously.

**See:** `fork_pattern.py`

---

### Pattern 2: Join (Fanin)

**Topology:**
```
source_A ─┐
source_B ─┤→ processor → sink
source_C ─┘
```

**Characteristics:**
- Multiple independent sources
- One processor
- One sink
- Sources produce data independently

**When to use:**
- Aggregate data from multiple sources
- All sources need same processing
- Merge different data streams

**Example:** Multiple cameras feeding images to one processor.

**See:** `join_pattern.py`

---

### Pattern 3: Diamond (Fork + Merge)

**Topology:**
```
        ┌→ process_A ─┐
source ─┤             ├→ merge → sink
        └→ process_B ─┘
```

**Characteristics:**
- Paths fork (fanout)
- Parallel processing
- Paths merge back together (fanin or merge_synch)
- Results are synchronized

**When to use:**
- Process data multiple ways in parallel
- Need to combine results from all paths
- Want synchronized merging (results stay paired)

**Example:** Analyze text for uppercase AND length, then combine into tuple.

**See:** `diamond_pattern.py`

---

### Pattern 4: General DAG (Directed Acyclic Graph)

**Topology:**
```
source_A ─┬→ proc_1 ─┬→ proc_3 ─┐
          │          │          ├→ merger → sink
source_B ─┴→ proc_2 ─┴→ proc_4 ─┘
```

**Characteristics:**
- Arbitrary complexity
- Multiple sources, processors, sinks
- Can combine fork, join, diamond patterns
- Any acyclic structure is valid

**When to use:**
- Complex data pipelines
- Multi-stage processing with validation
- Real-world systems with multiple concerns

**Example:** Multi-source data pipeline with validation, processing, and aggregation.

**See:** `general_dag.py`

---

## Comparing the Patterns

| Pattern | Sources | Sinks | Paths Merge? | Use Case |
|---------|---------|-------|-------------|----------|
| **Fork** | 1 | Multiple | No | Parallel processing, separate results |
| **Join** | Multiple | 1 | Yes (at processor) | Aggregate independent streams |
| **Diamond** | 1 | 1 | Yes (synchronized) | Parallel then combine results |
| **General DAG** | Any | Any | Maybe | Complex pipelines |

---

## How to Design Your Network Topology

### Step 1: Identify Components

Ask yourself:
1. **How many data sources?** (Files, APIs, sensors, etc.)
2. **What processing steps?** (Validation, transformation, analysis)
3. **How many outputs?** (Databases, files, dashboards)
4. **Do any paths need to merge?** (Synchronize or aggregate)

### Step 2: Choose Pattern(s)

- **One source, multiple analyses** → Fork
- **Multiple sources, one analysis** → Join
- **Parallel processing + combine results** → Diamond
- **Complex pipeline** → General DAG

### Step 3: Draw It First

Before writing code, draw your topology:
```
[Source] → [Validate] ─┬→ [ProcessA] → [SinkA]
                       └→ [ProcessB] → [SinkB]
```

This helps you see:
- Where data flows
- Where parallelism happens
- Where bottlenecks might occur

### Step 4: Implement as Network
```python
network([
    (source, validate),
    (validate, process_a),
    (validate, process_b),
    (process_a, sink_a),
    (process_b, sink_b)
])
```

---

## Key Design Principles

### Principle 1: Acyclic = One Direction

**Data flows forward only:**
```
✓ Good: A → B → C
✗ Bad:  A → B → A
```

**Why:** Acyclic networks always terminate cleanly.

### Principle 2: Any Acyclic Topology is Valid

**You can build:**
- Simple pipeline (A → B → C)
- Complex DAG (multiple branches, merges, levels)
- Anything in between

**As long as:** No cycles (no path from node back to itself).

### Principle 3: Parallelism is Free

**When paths split:**
```
    ┌→ fast →┐
A ──┤        ├→ D
    └→ slow →┘
```

- Both paths run concurrently
- Fast path doesn't wait for slow path
- Maximum throughput

### Principle 4: Merge Points Matter

**Independent merge (fanin):**
```
A ─┐
   ├→ processor
B ─┘
Messages interleave, no synchronization
```

**Synchronized merge (merge_synch):**
```
    ┌→ proc_A ─┐
src ┤          ├→ merge_synch
    └→ proc_B ─┘
Messages stay paired, waits for all paths
```

**Choose based on whether results must stay synchronized.**

---

## Common Mistakes

### Mistake 1: Accidentally Creating Cycles
```python
# ❌ Wrong - creates a cycle!
network([
    (A, B),
    (B, C),
    (C, A)  # Back to A - cycle!
])
```

**Fix:** Always flow forward. No node should connect back to a previous node.

### Mistake 2: Confusing Fork and Diamond
```python
# This is FORK (paths don't merge):
network([
    (src, proc_A),
    (src, proc_B),
    (proc_A, sink_A),
    (proc_B, sink_B)
])

# This is DIAMOND (paths merge):
network([
    (src, proc_A),
    (src, proc_B),
    (proc_A, merger),
    (proc_B, merger)
])
```

**Fork** = paths diverge and stay separate  
**Diamond** = paths diverge then reconverge

### Mistake 3: Not Drawing First

**Problem:** Jump straight to code without visualizing topology.  
**Result:** Confusing code, unclear data flow, hard to debug.

**Fix:** Always draw your topology first, even if just ASCII art.

### Mistake 4: Creating Bottlenecks
```python
# ❌ Bottleneck - all sources → one slow processor
network([
    (fast_src_1, slow_processor),
    (fast_src_2, slow_processor),
    (fast_src_3, slow_processor)
])
```

**Fix:** Add parallelism or optimize the bottleneck node.

---

## Pattern Selection Guide

**Choose the right pattern for your problem:**

### Use Fork When:
- ✓ One source, multiple analyses
- ✓ Results should stay separate
- ✓ Example: Image → thumbnail + metadata

### Use Join When:
- ✓ Multiple sources, same processing
- ✓ Aggregate streams
- ✓ Example: Multiple logs → one analyzer

### Use Diamond When:
- ✓ Parallel processing, then merge
- ✓ Need synchronized results
- ✓ Example: Text → sentiment + keywords → combined report

### Use General DAG When:
- ✓ Complex pipeline
- ✓ Multiple stages and concerns
- ✓ Example: Multi-source ETL with validation

---

## Next Steps

You now understand how to design acyclic network topologies!

**Practice:**
1. Run each pattern example: `fork_pattern.py`, `join_pattern.py`, `diamond_pattern.py`, `general_dag.py`
2. Draw topologies for problems you want to solve
3. Identify which pattern(s) fit your use case
4. Start with simple patterns, build to complex DAGs

**Next modules will apply these patterns to real domains:**
- **Module 08: Text Processing** - NLP pipelines
- **Module 09: Numeric/Data Science** - NumPy, pandas
- **Module 10: Machine Learning** - scikit-learn  
- **Module 11: AI Agents** - Claude integration

**Later: Cyclic Networks**
Once you master acyclic topologies, we'll introduce cycles for:
- Iterative refinement
- Feedback loops
- Stateful processing

**Want to experiment?** 
- Modify the examples to create your own topologies
- Combine patterns (fork inside a diamond, etc.)
- Design networks for problems in your domain

---

## Quick Reference

**The Four Patterns:**
```python
# Fork: One source → multiple processors → separate sinks
network([
    (src, proc_A), (src, proc_B),
    (proc_A, sink_A), (proc_B, sink_B)
])

# Join: Multiple sources → one processor → one sink
network([
    (src_A, proc), (src_B, proc), (src_C, proc),
    (proc, sink)
])

# Diamond: Fork → parallel → merge → sink
network([
    (src, proc_A), (src, proc_B),
    (proc_A, merger), (proc_B, merger),
    (merger, sink)
])

# General DAG: Arbitrary acyclic structure
network([
    (src_A, validate), (src_B, validate),
    (validate, proc_1), (validate, proc_2),
    (proc_1, merge), (proc_2, merge),
    (merge, sink)
])
```

**Remember:**
- Acyclic = no loops
- Draw topology before coding
- Choose pattern based on problem structure
- Any acyclic topology is valid!

---

**Questions?** Review the pattern examples or check [Troubleshooting](../../docs/troubleshooting.md).