# Layered Documentation Strategy for DisSysLab

## Goal
Create documentation that serves students with little programming experience who need to USE, UNDERSTAND, and MAINTAIN the system.

---

## Layer 1: High-Level Overview (Start Here)
**File: `docs/HOW_IT_WORKS.md`**

**Purpose:** Give students the mental model BEFORE diving into code

**Content:**
- "What happens when you run `g.run_network()`?"
- Visual diagrams showing message flow
- Concrete examples traced step-by-step
- Non-technical language
- Links to specific functions for deeper diving

**Audience:** Every student, read this first

**Length:** 1-2 pages

---

## Layer 2: Module-Level Documentation (Navigate)
**Location:** Module docstrings at top of each file

**Purpose:** Orient students within a specific file

**Content:**
- What this module does (1-2 paragraphs)
- Key classes and their responsibilities
- When students would need to modify this file
- Cross-references to HOW_IT_WORKS.md

**Example:**
```python
# dsl/graph.py
"""
Network Topology Construction and Compilation

This module converts student-written network definitions into executable graphs.
It handles:
- Parsing edges: (source, transform, sink) → internal representation
- Port resolution: Figuring out which ports connect to which
- Fanout/Fanin detection: Auto-inserting Broadcast/Merge agents
- Graph validation: Ensuring all ports are connected correctly

Students typically don't modify this file unless adding new graph features.

See docs/HOW_IT_WORKS.md for big-picture overview.
See docs/GRAPH_INTERNALS.md for detailed algorithm explanations.
"""
```

**Audience:** Students working on specific parts of the system

**Length:** 2-3 paragraphs per module

---

## Layer 3: Function-Level Documentation (Deep Dive)
**Location:** Detailed docstrings for each function

**Purpose:** Understand exactly what each function does and how to use/modify it

### Format for Complex Functions:
```python
def function_name(args) -> ReturnType:
    """
    [One-line summary]
    
    [2-3 paragraph explanation of what this does and why]
    
    **When is this called?**
    [Explain the context - when in the compilation process]
    
    **What problem does this solve?**
    [Explain the student's perspective - why we need this]
    
    **How does it work?**
    [High-level algorithm steps]
    
    **Example walkthrough:**
    [Complete traced example showing input → output]
    
    **Common issues:**
    [What goes wrong and how to debug]
    
    Args:
        [Parameter descriptions]
    
    Returns:
        [Return value description]
    
    Raises:
        [Error conditions]
    """
```

### Format for Simple Functions:
```python
def simple_function(obj) -> str:
    """
    [One-line summary]
    
    [1-2 sentences of explanation]
    
    Args:
        obj: [Description]
    
    Returns:
        [Description]
    """
```

**Audience:** Students debugging or modifying specific functions

**Key principle:** Include complete traced examples (like `_infer_roles()`)

---

## Layer 4: Detailed Algorithm Documentation (Reference)
**Files:** `docs/GRAPH_INTERNALS.md` and `docs/CORE_INTERNALS.md`

**Purpose:** Deep technical reference for advanced modifications

**Content:**
- Deep technical explanations
- Algorithm pseudocode
- Edge cases and corner cases
- Performance considerations
- Comparison with alternative approaches

**Audience:** Advanced students modifying internals (small subset)

**Length:** As long as needed for complete understanding

---

## Documentation Standards

### Include Troubleshooting in Every Layer

**In HOW_IT_WORKS.md:**
- Common high-level errors ("My network won't run")
- Links to detailed troubleshooting

**In function docstrings:**
- Common errors from this specific function
- How to debug them
- What the error messages mean

**Example:**
```python
def network(edges):
    """
    ...
    
    **Common student mistakes:**
    - "TypeError: Edge node must be Agent..." 
      → You passed a function instead of an agent.
      Make sure you wrapped it with source_map/transform_map/sink_map first!
    
    - "Port 'in' is not connected..." 
      → Every port must be connected.
      Check that each agent has both inputs and outputs connected.
    """
```

### Use Visual Diagrams

**Include in HOW_IT_WORKS.md:**
- Message flow diagrams
- Threading model visualization
- Queue connection diagrams

**ASCII art is fine for inline docs:**
```
source → [queue] → transform → [queue] → sink
  |                    |                   |
[thread 1]        [thread 2]          [thread 3]
```

### Provide Complete Examples

**Every complex function should include:**
- Input example
- Step-by-step trace
- Output example

**Follow the pattern from `_infer_roles()`:**
- Example 1: Simple case
- Example 2: Edge case
- Example 3: Complex real-world case

### Cross-Reference Liberally

**Link between layers:**
- HOW_IT_WORKS.md → specific functions
- Function docstrings → HOW_IT_WORKS.md
- Function docstrings → related functions
- Module docstrings → external docs

---

## Hybrid Approach - Recommended Starting Point

### Step 1: Create `docs/HOW_IT_WORKS.md` (1-2 pages)
- Visual overview of entire system
- "From `network([...])` to running threads"
- Links to deeper docs

**Time estimate:** 2 hours

### Step 2: Improve module docstrings in `graph.py` and `core.py`
- Add comprehensive module-level docstring to each file
- 1-2 paragraphs, very accessible

**Time estimate:** 1 hour

### Step 3: Enhance key function docstrings
- `network()` - entry point
- `Graph.compile()` - topology processing
- `Network.compile()` - execution setup
- `Agent` class - base for all agents
- Include complete traced examples in each

**Time estimate:** 4 hours

### Step 4: Add troubleshooting sections
- Common errors students encounter
- How to debug them
- In function docstrings and HOW_IT_WORKS.md

**Time estimate:** 2 hours

**Total for hybrid approach: ~8-10 hours**

---

## Later Enhancements (If Needed)

### Create deep-dive references:
- `docs/GRAPH_INTERNALS.md` - Fanin/fanout algorithm details
- `docs/CORE_INTERNALS.md` - Threading and queue implementation

**Only create these if:**
- Students are modifying core algorithms
- Advanced features are being added
- Performance tuning is required

---

## Success Criteria

**Layer 1 is successful if:**
- A new student can read HOW_IT_WORKS.md and build their first network
- Students understand the big picture without reading code

**Layer 2 is successful if:**
- A student can find the right file to modify
- Students understand what each module is responsible for

**Layer 3 is successful if:**
- A student can understand any function by reading its docstring
- Students can debug errors using the information provided
- Students can modify functions confidently

**Layer 4 is successful if:**
- Advanced students can extend the system with new features
- Algorithm design decisions are clear