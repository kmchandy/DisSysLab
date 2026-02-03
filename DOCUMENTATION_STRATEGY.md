# DisSysLab Documentation Strategy

This document describes our layered approach to documentation, designed to serve different audiences and use cases.

---

## Documentation Layers

### Layer 1: Quick Start (Getting Started)
**Audience:** First-time users, students starting Module 1  
**Goal:** Get something working in 5 minutes

**Files:**
- `README.md` (project root)
- `docs/quickstart.md` (if README gets too long)

**Content:**
- Installation instructions
- Absolute minimal example (3-5 lines of code)
- "You just built a distributed system!" moment
- Link to full tutorial

---

### Layer 2: Learning Path (Tutorial)
**Audience:** Students working through course modules  
**Goal:** Progressive understanding through examples

**Files:**
- `modules/basic/README.md` - Fanin/fanout patterns
- `modules/filtering/README.md` - None-dropping behavior
- `modules/numeric/README.md` - NumPy/pandas integration
- `modules/ml/README.md` - Machine learning pipelines
- Additional module READMEs as needed

**Content Structure (per module):**
1. What concept does this teach?
2. Network topology diagram (ASCII art)
3. Code walkthrough with explanations
4. Running the example
5. Key takeaway
6. Exercises to try

**Progression:**
- Start simple (3-node pipeline)
- Add complexity gradually (fanin, fanout, multi-port)
- Build to real applications (ML, data pipelines)

---

### Layer 3: Understanding the System (Conceptual)
**Audience:** Students who want to understand "how it works"  
**Goal:** Mental model of the entire system

**Files:**
- `docs/HOW_IT_WORKS.md` - Complete system overview
- `docs/CONCEPTS.md` - Core concepts in depth
- `docs/MESSAGE_FLOW.md` - How messages travel through networks

**Content:**
- From code to running system (step-by-step)
- Visual diagrams of compilation and execution
- Message flow tracing
- Why design decisions were made
- FAQ addressing common confusion points

---

### Layer 4: Reference (API Documentation)
**Audience:** Students building their own applications  
**Goal:** Quick lookup of syntax and parameters

**Files:**
- `docs/API_REFERENCE.md` - Complete API docs
- `docs/DECORATOR_REFERENCE.md` - All three decorators
- `docs/NETWORK_REFERENCE.md` - Network definition syntax

**Content:**
- Function signatures with type hints
- Parameter descriptions
- Return values and side effects
- Short examples for each function
- Links to full examples

---

### Layer 5: Deep Dive (Internals)
**Audience:** Advanced students, contributors, instructors  
**Goal:** Complete understanding of implementation

**Files:**
- `docs/ARCHITECTURE.md` - System architecture
- `docs/GRAPH_INTERNALS.md` - Topology compilation
- `docs/THREADING_MODEL.md` - Concurrency details
- `docs/QUEUE_SYSTEM.md` - Message passing internals

**Content:**
- How `network()` parses topology
- How `compile()` creates agents and queues
- Threading model and synchronization
- Why certain design choices were made
- Performance considerations

---

### Layer 6: Troubleshooting and Patterns
**Audience:** Everyone (referenced when stuck)  
**Goal:** Solve problems quickly

**Files:**
- `TROUBLESHOOTING.md` - Common errors and fixes
- `docs/PATTERNS.md` - Common design patterns
- `docs/DEBUGGING.md` - Debugging strategies

**Content:**
- Common error messages with explanations
- "If you see X, it means Y, try Z"
- Debugging techniques (print messages, trace flow)
- Design patterns (filtering, aggregation, routing)
- Performance tips

---

## Cross-Referencing Strategy

Each documentation layer links to others:

- **Quick Start** → Tutorial (Module 1)
- **Module READMEs** → How It Works, API Reference
- **How It Works** → Architecture (for curious students)
- **API Reference** → Module examples
- **Troubleshooting** → Relevant concepts, examples

---

## Writing Guidelines

### For Student-Facing Docs (Layers 1-3):
- Use second person ("you write a function...")
- Focus on concepts over implementation details
- Include visual diagrams (ASCII art is fine)
- Explain *why* things work this way
- Use encouraging, supportive tone
- Lots of examples

### For Reference Docs (Layers 4-5):
- Be precise and complete
- Use technical terminology accurately
- Include type signatures
- Focus on *what* and *how*, less on *why*
- Keep examples minimal and focused

### For All Documentation:
- One concept per section
- Code examples that actually run
- Link to related docs
- Keep up to date with code changes

---

## Maintenance Plan

- **After each code change:** Update affected API docs
- **After adding a module:** Write module README
- **Monthly:** Review for broken links and outdated info
- **After course offering:** Incorporate student feedback

---

## Documentation Checklist

Before releasing version 1++:
- [ ] All Layer 1 (Quick Start) complete
- [ ] All Layer 2 (Modules) have READMEs
- [ ] Layer 3 (How It Works) complete
- [ ] Layer 4 (API Reference) complete
- [ ] Layer 6 (Troubleshooting) has common issues covered
- [ ] All documentation reviewed and tested
- [ ] Student feedback incorporated

---

*Last updated: January 2026*