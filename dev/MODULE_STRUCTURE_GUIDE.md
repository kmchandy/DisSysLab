# Module Structure Guide

**Purpose:** Standard structure for DisSysLab teaching modules to ensure consistency and optimal learning experience.

**Location:** Save as `dev/MODULE_STRUCTURE_GUIDE.md`

---

## Core Principle

Each module should be **self-contained** and follow a consistent pattern so students know what to expect.

## Directory Structure
```
module_XX_topic_name/
├── README.md                    # The teaching content (MOST IMPORTANT!)
├── __init__.py                  # Makes it a package
├── example.py                   # Main working example
├── helpers.py                   # Helper functions (optional, only if needed)
└── exercises/                   # Optional: practice problems
    ├── exercise_1.py           # Starter code with TODOs
    ├── solution_1.py           # Complete solution
    ├── exercise_2.py
    └── solution_2.py
```

## File Contents

### `README.md` - The Heart of the Module (Template)
```markdown
# Module XX: Topic Name

[One-sentence description of what this module teaches]

## What You'll Learn

- Concept 1
- Concept 2  
- Concept 3

## The Problem We're Solving

[2-3 sentences: Why does this pattern matter? What real-world problem does it solve?]

## Network Topology

[ASCII diagram showing the network structure]
```
source1 ─┐
         ├─→ merger ─→ processor ─→ sink
source2 ─┘