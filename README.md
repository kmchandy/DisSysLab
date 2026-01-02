# 🕸️ DisSysLab — Build distributed apps by connecting functions

**DisSysLab (aka `dsl`)** is a Python framework that helps you build distributed programs. A program is represented by a directed graph in which each node is a Python function. The Python functions at nodes do not use parallel programming primitives such as threads or send/receive messages. You can build distributed programs using **dsl** if you are familiar with elementary programming.

**dsl** is designed to introduce first-year undergraduates to distributed programs. A goal is to help each student build distributed system applications that specifically interest her, and to do so easily. This is done by using **dsl** to connect functions in widely-used libraries such as Scikit and Gemini. **dsl** is an early release; it will evolve, and feedback is welcome.

Edges in the graph carry messages from function to function. The functions at the nodes run concurrently. We call a node of the graph an **agent**. You specify a graph by its list of edges. Here is an example of a graph `g`with three agents -- `data_source`, `data_transformer`, and `data_sink` and two edges: (1) an edge from `data_source` to `data_transformer` and (2) an edge from `data_transformer` to `data_sink`.

```python
from dsl import network

g = network([(data_source, data_transformer), (data_transformer, data_sink)])

```

You can specify the agents that generate data, such as `data_source` in the example, as Python functions or use **dsl** wrappers to sensors, RSS feeds, or other sources of data. Likewise a `data_sink` can be a Python function, or a wrapper that controls an actuator or stores a stream of data in a database. Similarly, can write your own function for the `data_transformer` node or choose a function from Python's rich libraries.

You can create arbitrary graphs. The initial modules of this description use acyclic graphs. Later modules deal with graphs that contain cycles.


## TL;DR – try it

```bash
git clone https://github.com/kmchandy/DisSysLab.git
cd DisSysLab
python -m venv .venv && source .venv/bin/activate   # Windows: .\.venv\Scripts\Activate.ps1
python -m pip install -e .
python -m modules.ch01_networks.simple_network
```


## 👉 Start Here
Make sure that you have the keys you need for your services (eg OpenAI) in your .env file.

[Module 1. An introduction to dsl.](./modules/ch01_networks/README_1.md) 


## Modules

1) **Module 1 — Intro** → [modules/ch01_networks/README_1.md](modules/ch01_networks/README_1.md)  
2) **Module 2 — Sources** → [modules/ch02_sources/README_1.md](modules/ch02_sources/README_1.md)  
3) **Module 3 — OpenAI agents** → [modules/ch03_GPT/README_1.md](modules/ch03_GPT/README_1.md)  
4) **Module 4 — Numerics** → [modules/ch04_numeric/README.md](modules/ch04_numeric/README.md)

