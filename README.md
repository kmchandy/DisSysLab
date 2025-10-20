# 🕸️ DisSysLab — Build distributed apps by connecting functions

**DisSysLab (aka `dsl`)** is a lightweight teaching framework where you build distributed programs as **graphs of plain Python callables**. Each node is just a function — often a call into a familiar library (NumPy/SciPy, requests, OpenAI, etc.). Edges carry messages. Agents run concurrently.

DSL is designed for first-year undergrads. This is an early release. It will evolve and feedback is welcome.

---

## Core idea

- A **program is specified as directed graph** where nodes are agents and edges are message channels.
- An **agent is a callable**. It can be:
  - a pure Python function (`def f(x): ...`),
  - a class instance with `__call__`,
  - a thin wrapper around a **standard library** function (NumPy, SciPy, requests),
  - or a service call (e.g., OpenAI) behind a simple adapter.
  
- You don’t use concurrency primitives such as ***send***, ***receive***, and ***threads***.

```python
from dsl import network

def src():
   for i in range(10):              # zero-arg source → yields messages
    yield i

def double(x): return 2 * x     # transform
def show(x): print(x)           # sink

g = network([
  (src, double),
  (double, show),
])
g.run_network()
```

## 👉 Next
[Module 1. An introduction to dsl.](./modules/ch01_networks/README_1.md) 
