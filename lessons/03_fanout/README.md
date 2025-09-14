# 🔀 Lesson 3 Fan-Out Blocks

## 🎯 Goal
Build networks using **fanout** (one input, multiple outputs) blocks  

---

## 📍 What We’ll Build
We will build networks with three examples of fanout blocks: **broadcast**, **split_two_way** and **split_multiway**.


## Example 1: Broadcast

**Blocks in this example:**
- block name: **"source"**
  - execution: **FromList((['a', 'b', 'c']))** generates messages 'a', 'b', 'c'
- block name: **"broadcast**
  - outports: **"out_0"**, **"out_1"**, **"out_2"**,
  - execution: **Broadcast(["out_0", "out_1", "out_2"])**, sends a copy of the stream of messages it receives from its single inport **"in"** on each of its outports.
- block name: **"sink_0"**, **"sink_1"**, **"sink_2"**
  - execution: **ToList(results_0)**, **ToList(results_1)**, **ToList(results_1)** stores the stream of messages that it receives in its inport on the specified list.



```
# lessons.03_fanout.broadcast.py

from dsl.kit import Network, FromList, Broadcast, ToList

def broadcast_example():
    results_0 = []  # Holds results sent to sink_0
    results_1 = []  # Holds results sent to sink_1
    results_2 = []  # Holds results sent to sink_2

    net = Network(
        blocks={
            "source": FromList(['a', 'b', 'c', 'd']),
            "broadcast": Broadcast(outports=["out_0", "out_1", "out_2"]),
            "sink_0": ToList(results_0),
            "sink_1": ToList(results_1),
            "sink_2": ToList(results_2),
        },
        connections=[
            ("source", "out", "broadcast", "in"),
            ("broadcast", "out_0", "sink_0", "in"),
            ("broadcast", "out_1", "sink_1", "in"),
            ("broadcast", "out_2", "sink_2", "in"),
        ],
    )

    net.compile_and_run()
    assert results_0 == ['a', 'b', 'c', 'd']
    assert results_1 == ['a', 'b', 'c', 'd']
    assert results_2 == ['a', 'b', 'c', 'd']
```

## ▶️ Run It

```
python -m lessons.03_fanout.broadcast.py
```


## Example 2 SplitBinary
Similar to example 1 except that **Broadcast()** is replaced by **SplitBinary(f)** where **f** is a boolean function that has an input message and outputs True if the message (a number) is odd. 

**Blocks in this example:**
- block name: **"split_binary**
  - outports: **"out_0"**, **"out_1"**,
  - execution: **SplitBinary(f)**, sends the messages it receives for which **f** returns True on **out_1** and other messages on **out_0**.

```
# lessons.03_fanout.spit_binary.py
from dsl.kit import Network, FromList, ToList, SplitBinary
def split_binary():
    """
    Outport "out_0" receives values for which func returns False.
    Outport "out_1" receives values for which func returns True.
    Stops when any inport yields '__STOP__'.
    """
    def f(x):
        return x % 2

    results_0 = []
    results_1 = []
    network = Network(
        blocks={
            "source": FromList([0, 1, 2, 3, 4]),
            "split_binary": SplitBinary(func=f),
            "sink_0": ToList(results_0),
            "sink_1": ToList(results_1)
        },
        connections=[
            ("source", "out", "split_binary", "in"),
            ("split_binary", "out_0", "sink_0", "in"),
            ("split_binary", "out_1", "sink_1", "in")
        ]
    )
    network.compile_and_run()
    assert results_0 == [0, 2, 4]
    assert results_1 == [1, 3]
```
## ▶️ Run It

```
python -m lessons.03_fanout.split_binary.py
```

## 🧠 Key Takeaways

- **You can build arbitrary networks** with generators, transformers, recorders, fanout and (discussed next) fanin blocks.

### 🚀 Coming Up

Fanin blocks with multiple inputs and a single output

👉 **Next up: [Lesson 4 — Fanin Blocks.](../04_fanin/README.md)**