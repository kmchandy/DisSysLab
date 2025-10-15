# 🕸 1.6 • Simple Network — Fan-Out & Fan-In

This page shows how to build an **arbitrary graph** (not just a linear pipeline) with **fan-out** (one node → many) and **fan-in** (many → one).

---

## 🎯 Goal

- Create a small network with two sources that **fan-out** to two transforms and then **fan-in** to a single sink.
- Observe interleaved outputs as items flow concurrently from multiple sources.

---

## 💻 Example: Arbitrary Graph with Fan-Out / Fan-In

```python
# modules.ch01_networks.simple_network

from dsl import network
import time

# -----------------------------------------------------------
# Sources
# -----------------------------------------------------------

def from_list_0():
    for item in ["A", "B"]:
        yield item
        time.sleep(0.12)

def from_list_1():
    for item in ["X", "Y", "Z"]:
        yield item
        time.sleep(0.1)

# -----------------------------------------------------------
# Transforms
# -----------------------------------------------------------

def lower(v):
    return v.lower()

def add_bangs(v):
    return v + "!!"

# -----------------------------------------------------------
# Sink (fan-in target)
# -----------------------------------------------------------

results = []
def to_results(v): 
    results.append(v)

# -----------------------------------------------------------
# Graph wiring
# - Fan OUT: each source feeds BOTH transforms
# - Fan IN: both transforms feed the SAME sink
# -----------------------------------------------------------

g = network([
    (from_list_0, lower), 
    (from_list_1, lower),
    (from_list_0, add_bangs), 
    (from_list_1, add_bangs),
    (lower, to_results), 
    (add_bangs, to_results)
])

g.run_network()

if __name__ == "__main__":
    print(set(results))
    assert set(results) == {"A!!", "B!!", "X!!", "Y!!", "Z!!", "a", "b", "x", "y", "z"}
```

---

## ▶️ Run the demo

```bash
python3 -m modules.ch01_networks.simple_network
```

You’ll see outputs interleaved depending on source timing, with both lowercase variants and “!!” variants collected in `results`.

---

## 🧩 Fan-Out and Fan-In

- **Fan-Out:** Messages from a node can be broadcast to multiple nodes (e.g., `from_list_0 → lower` and `from_list_0 → add_bangs`).
- **Fan-In:** A node can receives messages from multiple nodes (e.g., `lower → to_results` and `add_bangs → to_results`).

---

## 🧠 Key Concepts

- **Arbitrary graphs:** You can create networks with arbitrary topologies. (Note: Later we discuss termination detection of networks with cycles. )

---


## 👉 Next

 [Explore different types of sources](../ch02_sources//README_1.md).
