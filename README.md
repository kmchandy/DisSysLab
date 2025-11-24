# 🕸️ DisSysLab — Build distributed apps by connecting functions

**DisSysLab (aka `dsl`)** is a Python framework that helps you build distributed programs. A program is represented by a directed graph in which each node is a Python function which receives and sends messages. Often, the function is selected from widely-used libraries such as Numpy, OpenAI and Gemini. Edges in the graph carry messages from function to function. The functions at the nodes run concurrently. A node of the graph is called an agent.

DisSysLab is designed to introduce first-year undergraduates to distributed programs. This is an early release; it will evolve, and feedback is welcome.

## TL;DR – try it

```bash
git clone https://github.com/kmchandy/DisSysLab.git
cd DisSysLab
python -m venv .venv && source .venv/bin/activate   # Windows: .\.venv\Scripts\Activate.ps1
python -m pip install -e .
python -m modules.ch01_networks.simple_network
```

---

## Core idea

- A **program is specified as directed graph** where nodes are agents and edges are message channels.
- An **agent is a callable**. It can be:
  - a pure Python function (`def f(x): ...`),
  - a class instance with `__call__`,
  - a wrapper around a **standard library** function (NumPy, SciPy, requests),
  - or a service call (e.g., OpenAI) behind a simple adapter.
  
- You specify a graph by its list of edges. Here is an example of a graph `g`with three agents -- `data_source`, `compute`, and `data_sink` and two edges: (1) an edge from `data_source` to `compute` and (2) an edge from `compute` to `data_sink`.

```python
from dsl import network

g = network([(data_source, compute), (compute, data_sink)])

```

You can specify the agents that generate data, such as `data_source` in the example, as functions or wrappers to sensors, RSS feeds or other sources. Likewise you can write your own function for `data_sink` or use a wrapper that stores a stream of data in a database, controls an actuator, or carries out other actions. Similarly, can write your own function for the `compute` node or choose a function from Python's rich libraries or interfaces to OpenAI, Gemini or other services.

You can create arbitrary graphs. The initial modules of this description use acyclic graphs. Later modules deal with graphs that contain cycles.


## 👉 Start Here
[Module 1. An introduction to dsl.](./modules/ch01_networks/README_1.md) 


## Modules

1) **Module 1 — Intro** → [modules/ch01_networks/README_1.md](modules/ch01_networks/README_1.md)  
2) **Module 2 — Sources** → [modules/ch02_sources/README_1.md](modules/ch02_sources/README_1.md)  
3) **Module 3 — OpenAI agents** → [modules/ch03_GPT/README_1.md](modules/ch03_GPT/README_1.md)  
4) **Module 4 — Numerics** → [modules/ch04_numeric/README.md](modules/ch04_numeric/README.md)

