# 📂 DisSysLab Directory Structure

This document maps the planned layout of the DisSysLab repository.  
Most directories have `README.md` and examples).

---
## Repository Overview
```
DisSysLab/
├─ README.md
├─ README_Directory.md          # this file
├─ dsl/                         # the library most users import
│  ├─ graph.py                  # Graph DSL (spec)
│  ├─ core.py                   # runtime: Agent, Network, STOP, plumbing
│  ├─ ops/                      # tiny, dependency-free callables (pure Python)
│  │  ├─ sources/               # e.g. from_list(...)
│  │  └─ sinks/                 # e.g. to_list(...)
│  |  └─ transforms/            # e.g. common_transforms  
│  ├─ blocks/                   # runtime blocks used by Network
│  │  ├─ source.py              # Source
│  │  ├─ transform.py           # Transform
│  │  ├─ sink.py                # Sink
│  │  ├─ fanout.py              # Broadcast / Split
│  │  └─ fanin.py               # Merge (sync/async)
│  │  └─ graph_structures.py    # Pipeline and other graphs
│  ├─ connectors/               # data/app connectors (e.g., Google Sheets)
│  │  └─ sheets.py
│  └─ extensions/               # optional add-ons (heavy deps; install as extras)
│     ├─ llm/
│     │  └─ openai_agent.py     # OpenAIAgent.fn(...)
│     └─ ml/
│        └─ sklearn.py          # featurize(...), predict(...)
├─ examples/                    # runnable scripts (buffet for exploration)
│  ├─ graph_simple_source_sink.py
│  ├─ graph_openai_agent.py     # requires [llm]
│  └─ graph_sklearn_text_classify.py  # requires [ml]
├─ lessons/                     # 5–10 minute guided mini-tutorials
│  ├─ 01_networks_blocks_connections/
│  ├─ 02_msg_as_dict/
│  ├─ 03_fanout/
│  └─ 04_fanin/
├─ tests/                       # small pytest suite
│  ├─ test_graph_basics.py
│  ├─ test_broadcast.py
│  └─ test_validation.py
└─ user_interaction/            # CLI/UX helpers (optional)
```

## Top Level

- **dsl/** – Core library of blocks, agents, and utilities.
- **tests/** – Flat test suite, one file per concept/module.
- **lessons/** – 5-minute tutorials with narrative + runnable code.
- **examples/** – Standalone example applications (buffet for exploration).
- **user_interaction/** – UX helpers (CLI, prompts, Colab/Notebook widgets, wizards).
- **README.md** – Main project guide (quickstart, philosophy).
- **README_Directory.md** – This document (repository map).

---

## dsl/
- **graph.py** - How to develop distributed applications. `Graph' 'Edges', 'Node' specifications
- **core.py** – Foundation: `Agent`, `Network`, `System`, `STOP`, and core message-passing logic. Used by **graph.py**.
- **ops/** - Directory of simple functions used in **graph.py**
- **blocks** the building blocks of the DisSysLab framework.
- **connectors** interfaces to apps and databases
- **extensions** Functions used in **graph.py** to call large language models and other services.


## lessons/
Step-by-step, 5-minute,  `README.md` and short Python examples.

- `01_networks_blocks_connections/` — Basics: blocks + connections  
- `02_msg_as_dict/` — Messages that are dicts with keys and values  
- `03_fanout/` — Splitting streams into multiple streams
- `04_fanin/` — Combining multiple streams into a single stream

---

## examples/
A collection of standalone example applications for browsing and modifying.