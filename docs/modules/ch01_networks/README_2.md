## 🧩 1.2 Fanout and Fanin


## 🎯 Goal


- Understand behavior of **fanout** (multiple output edges from a node) and **fanin** (multiple input edges to a node.)
---

## 💻 Example of fanout
 
```python
# modules.ch01_networks.simple_broadcast

from dsl import network

def from_list():
    for item in ["hello", "world"]:
        yield item

results_0 = []
results_1 = []


def sink_0(item):
    results_0.append(item)


def sink_1(item):
    results_1.append(item)


# Define the network as a list of directed edges of a graph
g = network([(from_list, sink_0), (from_list, sink_1)])
g.run_network()

print(results_0)    # Output: ['hello', 'world']
print(results_1)    # Output: ['hello', 'world']
```
## 📍 Fanout
The messages output by a node are broadcast along each of the node's output edges.

## 💻 Example of fanin
 
```python
# modules.ch01_networks.simple_merge

from dsl import network
import time


def from_list_0():
    for item in ["A", "B"]:
        yield item
        time.sleep(0.06)


def from_list_1():
    for item in ["X", "Y", "Z"]:
        yield item
        time.sleep(0.05)


results = []
def to_results(v): results.append(v)


g = network([(from_list_0, to_results), (from_list_1, to_results)])
g.run_network()

print(results)
assert set(results) == {"A", "B", "X", "Y", "Z"}
```

---
## 📍 Fanin
The messages arriving along multiple edges at a node are merged nondeterministically and fairly. Messages sent along an edge arrive at the destination node eventually. The time that a message takes in transit along an edge is unknown. Even if message "X" is sent along the edge (from_list_1, to_results) before message "A" is sent along the edge (from_list_0, to_results) it is possible that "A" arrives at to_results before "X" does.


## 🧠 Key Concepts
- Fanout is a broadcast.
- Fanin is a fair merge.

## 👉 Next
[Drop messages in streams](./README_3.md) by returning ```None```.