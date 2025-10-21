# 🕸️ DisSysLab — Build distributed apps by connecting functions

**DisSysLab (aka `dsl`)** is a lightweight teaching framework where you build distributed programs as **graphs of plain Python callables**. Each node is just a function — often a call into familiar libraries (NumPy/SciPy, requests, OpenAI). Edges carry messages. Agents run concurrently.

DisSysLab is designed for first-year undergrads. This is an early release; it will evolve, and feedback is welcome.

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
  - a thin wrapper around a **standard library** function (NumPy, SciPy, requests),
  - or a service call (e.g., OpenAI) behind a simple adapter.
  
- You don’t use concurrency primitives such as ***send***, ***receive***, and ***threads***. Instead you connect functions.

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

## 👉 Start Here
[Module 1. An introduction to dsl.](./modules/ch01_networks/README_1.md) 


## Modules

1) **Module 1 — Intro** → [modules/ch01_networks/README_1.md](modules/ch01_networks/README_1.md)  
2) **Module 2 — Sources** → [modules/ch02_sources/README_1.md](modules/ch02_sources/README_1.md)  
3) **Module 3 — OpenAI agents** → [modules/ch03_GPT/README_1.md](modules/ch03_GPT/README_1.md)  
4) **Module 4 — Numerics** → [modules/ch04_numeric/README.md](modules/ch04_numeric/README.md)

