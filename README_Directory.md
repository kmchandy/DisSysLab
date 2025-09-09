# 📂 DisSysLab Directory Structure

This document maps the planned layout of the DisSysLab repository.  
Each directory has its own `README.md` (many with examples).

---
## Diagrams — File Structure


### Repository Overview

```
DisSysLab/
├─ README.md
├─ README_Directory.md
├─ dsl/
│  ├─ core.py
│  └─ block_lib/
│     ├─ sources/
│     │  ├─ source.py
│     │  ├─ source_lib/
│     │  │  ├─ lists.py
│     │  │  ├─ ....
│     │  └─ README.md
│     ├─ transformers/
│     │  ├─ transform.py
│     │  ├─ transform_lib/
│     │  │  ├─ sentiment.py
│     │  │  └─ ....
│     │  └─ README.md
│     ├─ sinks/
│     │  ├─ sink.py
│     │  ├─ sink_lib/
│     │  │  ├─ files.py
│     │  │  ├─ .....
│     │  └─ README.md
│     └─ routers/
│        ├─ fanin.py
│        ├─ fanout.py
│        └─ README.md
├─ tests/
│  ├─ ....
├─ chapters/
│  ├─ ch01_blocks_connections/
│  ├─ .....
├─ examples/
│  ├─ rss_to_console.py
│  ├─ ....
└─ user_interaction/          # CLI/UI/wizard
```


## Top Level

- **dsl/** – Core library of blocks, agents, and utilities.
- **tests/** – Flat test suite, one file per concept/module.
- **chapters/** – tutorials with narrative + runnable code.
- **examples/** – Standalone example applications (buffet for exploration).
- **user_interaction/** – UX helpers (CLI, prompts, Colab/Notebook widgets, wizards).
- **README.md** – Main project guide (quickstart, philosophy).
- **README_Directory.md** – This document (repository map).

---

## dsl/

- **core.py** – Foundation: `Agent`, `Network`, `System`, `STOP`, and core message-passing logic.

### block_lib/
Block library, grouped by role in a network.

#### sources/ — Generators of messages
- `source.py` — **Source** (inherits `SimpleAgent`; one outport `"out"`, no inports).
- `source_lib/` — **Package** of pure-Python helpers used by `Source`.
- `README.md` — Explains sources and shows basic usage.

#### transforms/ — Transformers of messages
- `transform.py` — **Transform** (tiny mapper; one inport `"in"`, one outport `"out"`).
- `transform_lib/` — **Package** of pure-Python transforms used by `Transform`.
  - `__init__.py` – Re-exports selected transforms (add more as you grow):
- `README.md` — Explains transforms with examples.
#### sinks/ — Recorders of messages (side effects)
- `sink.py` — **Sink** (inherits `SimpleAgent`; one inport `"in"`, no outports).
- `sink_lib/` — **Package** of pure-Python recorders used by `Sink`.
- `README.md` — Explains sinks and usage.
#### routers/ — Routing blocks (fan-in, fan-out)
- `fanin.py` — `MergeSynch`, `MergeAsynch` (combine multiple streams → one).
- `fanout.py` — `Broadcast`, `Split` (one stream → multiple outputs).
- `README.md` — Explains routing patterns.

#### connectors/
- connect to external apis such as Google sheets
---

## chapters/
Step-by-step tutorials. Each chapter has a `README.md` and short Python examples.

- `ch01_blocks_connections/` — Basics: blocks + connections  
- `ch02_messages_as_dicts/` — Messages with keys and values  
- `ch03_fanin/` — Combining multiple streams  
- `ch04_fanout/` — Splitting streams into branches  

---

## examples/
A collection of standalone example applications for browsing and modifying.