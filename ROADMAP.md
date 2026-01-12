# DisSysLab_1.0 → 1++ Roadmap

## Goal
Make DisSysLab_1.0 bulletproof, well-documented, and easily maintainable by first-year students before moving to version 2.0 (which adds cycles, global snapshots, termination detection, and concurrent modification handling).

---

## Phase 1: Code Solidification (Foundation)
*Goal: Make the code robust, debuggable, and maintainable*

1. **Add comprehensive error messages**
   - Improve error messages in `graph.py` (port connection errors, type errors)
   - Add validation in decorators (missing keys, type mismatches)
   - Create helper function to suggest fixes when errors occur

2. **Add logging/debugging infrastructure**
   - Optional `DEBUG=True` mode that shows message flow
   - Trace messages through the network (which agent sent what to whom)
   - Performance metrics (messages processed, queue sizes)

3. **Write unit tests**
   - Test each decorator independently
   - Test fanin/fanout insertion logic
   - Test multi-port agents
   - Test error conditions

4. **Code review and cleanup**
   - Consistent naming conventions
   - Remove any dead code
   - Add type hints throughout
   - Ensure all docstrings are complete and accurate

---

## Phase 2: Core Documentation (Understanding)
*Goal: Students can understand how everything works*

1. **`ARCHITECTURE.md`** - Big picture overview
   - How messages flow through the system
   - The role of queues, threads, agents
   - When to use decorators vs custom agents
   - Diagram of the execution model

2. **`dsl/core.py` documentation**
   - Detailed explanation of `Agent` base class
   - How `Network` compilation works
   - Threading model and queue management
   - Port reference system

3. **`dsl/graph.py` documentation**
   - How network topology is parsed
   - Fanin/fanout detection algorithm
   - How to debug graph construction issues

4. **`dsl/decorators.py` documentation**
   - When to use `source_map` vs `transform_map` vs `sink_map`
   - How the decorators wrap functions
   - Examples of common patterns

---

## Phase 3: Student-Facing Documentation (Learning)
*Goal: Students can build their own applications*

1. **Main `README.md`** (Project root)
   - What is DisSysLab?
   - Quick start guide
   - Link to tutorial modules
   - Installation instructions

2. **`TUTORIAL.md`** - Step-by-step guide
   - Module 1: Basic pipeline (source → transform → sink)
   - Module 2: Filtering with None
   - Module 3: Fanin and fanout
   - Module 4: Multi-port custom agents
   - Module 5: Building with NumPy/pandas
   - Module 6: Real-world example (data pipeline)

3. **Module READMEs** (One per module)
   - What concept this module teaches
   - Code walkthrough with line-by-line explanation
   - Exercises for students to modify the example
   - Common mistakes and how to fix them

4. **`TROUBLESHOOTING.md`**
   - Common error messages and what they mean
   - Debugging strategies
   - How to trace message flow
   - When to use custom agents vs decorators

---

## Phase 4: Examples and Patterns (Application)
*Goal: Show students what they can build*

1. **Create diverse example modules** (6-8 total)
   - `basic/` - Social media analysis (✅ done)
   - `drop_None/` - Filtering (✅ done)
   - `general_agents/` - Multi-port (✅ done)
   - `numeric/` - NumPy operations (matrix processing)
   - `data_pipeline/` - Read CSV → process → write results
   - `text_nlp/` - Text processing pipeline
   - `ml_pipeline/` - scikit-learn model training
   - `real_time/` - Rate-limited streaming data

2. **`PATTERNS.md`** - Common design patterns
   - Pattern: Filter and split
   - Pattern: Aggregation (collect N items then process)
   - Pattern: Pipeline with side effects (logging, metrics)
   - Pattern: Error handling and recovery
   - Pattern: Stateful transforms (counters, caches)

---

## Phase 5: Using Claude AI (Meta-learning)
*Goal: Teach students how to use AI to build distributed systems*

1. **`USING_CLAUDE.md`**
   - How to describe your application to Claude
   - Best prompts for building DSL applications
   - How to ask Claude to debug your code
   - Iterating with Claude on design

2. **Video/screencast (optional)**
   - Recording of building an application with Claude
   - Shows the conversation flow
   - Demonstrates debugging together

3. **Example conversation transcripts**
   - "I want to build X" → Claude helps design topology
   - "I'm getting error Y" → Claude helps debug
   - "How do I add feature Z?" → Claude suggests approach

---

## Phase 6: Polish and Package (Distribution)
*Goal: Make it easy to install and use*

1. **Package structure**
   - Proper `setup.py` or `pyproject.toml`
   - Version numbering scheme
   - Dependencies clearly specified

2. **Installation guide**
   - `pip install` instructions
   - Virtual environment setup
   - Verification tests

3. **Contributing guide**
   - How students can add their own examples
   - Code style guidelines
   - How to submit bug reports

4. **License and attribution**
   - Choose appropriate license
   - Credit contributors

---

## Recommended Order

### Sprint 1 (Most Critical)
**Focus: Core infrastructure documentation**

1. Phase 2.1-2.3 (Core documentation for graph.py, core.py)
2. Phase 3.3 (Module READMEs - document existing examples)
3. Phase 1.1 (Better error messages)

**Estimated time:** 2-3 weeks

---

### Sprint 2 (Student-Facing)
**Focus: Help students learn and build**

1. Phase 3.1 (Main README)
2. Phase 3.2 (Tutorial)
3. Phase 4.1 (Create 3-4 more diverse examples)

**Estimated time:** 2-3 weeks

---

### Sprint 3 (Advanced)
**Focus: Patterns and troubleshooting**

1. Phase 4.2 (Patterns document)
2. Phase 3.4 (Troubleshooting guide)
3. Phase 5.1 (Using Claude guide)

**Estimated time:** 1-2 weeks

---

### Sprint 4 (Polish)
**Focus: Production-ready**

1. Phase 1.2-1.4 (Debugging, tests, cleanup)
2. Phase 6 (Packaging)

**Estimated time:** 1-2 weeks

---

## What to Start With

**Immediate Priority: Document graph.py and core.py**

Start with **Phase 2.2 and 2.3** because:
1. The code is fresh in our minds (we just fixed the fanin/fanout bug)
2. These are the trickiest parts to understand
3. Good internal docs make writing student-facing docs easier
4. We already started with excellent `_infer_roles()` documentation

**First concrete steps:**
1. Create `docs/HOW_IT_WORKS.md` (high-level overview)
2. Add comprehensive module docstrings to `graph.py` and `core.py`
3. Enhance key function docstrings with examples and troubleshooting

**Success criteria for Sprint 1:**
- A student can read HOW_IT_WORKS.md and understand the system
- A student can read graph.py and core.py docstrings and understand each function
- A student encountering an error can debug it using the documentation