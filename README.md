## 🕸️ DisSysLab — Build distributed apps by connecting functions


**DisSysLab (aka `dsl`)** is a Python framework for building distributed programs. A program is represented by a directed graph in which each node is a Python callable. You do **not** write threads, locks, or send/receive calls. The **dsl runtime** runs the nodes concurrently and moves messages along edges.

**dsl** introduces first-year undergraduates to distributed programs. Each student builds distributed-system applications that interests that specific student. You build systems by connecting functions in widely used libraries, such as NumPy, and LLM APIs such as OpenAI. **dsl** is an early release; it will evolve, and feedback is welcome.

## The core idea

Edges carry **messages** (often Python dicts) from node to node. We call a node of the graph an **agent**. You specify a graph by its list of edges.

DisSysLab uses two main callable shapes:

1) **Sources**: yield a stream of messages  
2) **Transforms / Sinks**: take one message and return one message (transform) or return nothing/ignored (sink)

Example: a graph `g` with three agents—`data_source`, `data_transformer`, and `data_sink`, and `data_sink` and two edges: (1) `data_source` to `data_transformer` and (2) `data_transformer` to `data_sink`.

```python
from dsl import network

g = network([
    (data_source, data_transformer),
    (data_transformer, data_sink),
])
```

You can write agents as plain Python functions, or use dsl connectors/wrappers:

- **Sources:** sensors, RSS feeds, files, synthetic generators
- **Transforms:** library calls, filters, ML, LLM calls
- **Sinks:** console displays, JSONL/CSV recorders, databases, actuators

You can create arbitrary graphs. Early modules use acyclic graphs; later modules introduce cycles.

## TL;DR – try it

```bash
git clone https://github.com/kmchandy/DisSysLab.git
cd DisSysLab
python -m venv .venv && source .venv/bin/activate   # Windows: .\.venv\Scripts\Activate.ps1
python -m pip install -e .
python -m modules.ch01_networks.simple_network
```


## 👉 Start Here
Make sure that you have the keys you need for your services (eg OpenAI) in your .env file for modules 3 and 5. Start with 
**Module 1 — Intro** → [modules/ch01_networks/README_1.md](modules/ch01_networks/README_1.md) 


## Modules

1) **Module 1 — Intro** → [modules/ch01_networks/README_1.md](modules/ch01_networks/README_1.md)  
2) **Module 2 — Sources** → [modules/ch02_sources/README_1.md](modules/ch02_sources/README_1.md)  
3) **Module 3 — OpenAI agents** → [modules/ch03_GPT/README_1.md](modules/ch03_GPT/README_1.md)  
4) **Module 4 — Numerics** → [modules/ch04_numeric/README.md](modules/ch04_numeric/README.md)
5) **Module 5 — Use AI to build systems** → [modules/ch05_use_AI/README.md](modules/ch05_use_AI/README.md)

