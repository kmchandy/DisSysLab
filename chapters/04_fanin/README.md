# 🔀 Lesson 4 Fan-In Blocks

## 🎯 Goal
Build networks using **fanin** (one input, multiple outputs) blocks  

---

## 📍 What We’ll Build
We will build networks with **MergeSynch** and **MergeAsynch** blocks which have multiple inports and a single outport called **"out"**.


## Example 1: Synchronous Merge

**Blocks in this example:**
- block name: **"source_a**
  - execution: **FromListDelay(["HELLO", "GOOD", "HOW"], delay=0.1)** generates messages in the list with a delay of 0.1 seconds between messages.
- block name: **"source_b**
  - similar to source_a
sink: **sink**
- block name: **"merge_synch**
  - outports: **"a"**, **"b"**,
  - execution: **MergeSynch(inports, func)**, waits until a message is received from each inport and then outputs **func** applied to the list of messages.



```
# lessons.04_fanin.merge_synch_example

from dsl.kit import Network, FromListDelay, ToList, MergeSynch


def merge_synch_example():

    def f(pair):
        return pair[0] + pair[1]

    results = []
    network = Network(
        blocks={
            "source_a": FromListDelay(items=["HELLO", "GOOD", "HOW"], delay=0.1),
            "source_b": FromListDelay(items=[" world", " morning", " are you?"], delay=0.08),
            "merge_synch": MergeSynch(inports=["a", "b"], func=f),
            "sink": ToList(results)
        },
        connections=[
            ("source_a", "out", "merge_synch", "a"),
            ("source_b", "out", "merge_synch", "b"),
            ("merge_synch", "out", "sink", "in")
        ]
    )
    network.compile_and_run()
    assert results == ['HELLO world', 'GOOD morning', 'HOW are you?']
```

## ▶️ Run It

```
python -m lessons.04_fanin.merge_synch_example.py
```


## Example 1: Asynchronous Merge

**Blocks in this example:**
sources: **source_a**, **source_b**
sink: **sink**
- block name: **"merge_asynch**
  - outports: **"a"**, **"b"**,
  - execution: **MergeAsynch(inports, func)**, outputs **func** applied to the message that arrives on any port. Stops execution when **STOP** is received on either port.


```
# lessons.04_fanin.merge_asynch_example

from dsl.kit import Network, FromListDelay, ToSet, MergeAsynch


def merge_asynch_example():
    """

    """
    def f(msg, port):
        if port == "a":
            return msg + " " + msg
        else:
            return msg + "!!!"

    results = set()
    network = Network(
        blocks={
            "source_a": FromListDelay(items=["HELLO", "GOOD", "HOW"], delay=0.15),
            "source_b": FromListDelay(items=[" world", " morning", " are you?"], delay=0.09),
            "merge_asynch": MergeAsynch(inports=["a", "b"], func=f),
            "sink": ToSet(results)
        },
        connections=[
            ("source_a", "out", "merge_asynch", "a"),
            ("source_b", "out", "merge_asynch", "b"),
            ("merge_asynch", "out", "sink", "in")
        ]
    )
    network.compile_and_run()
    assert results == {'HELLO HELLO', 'GOOD GOOD', 'HOW HOW',
                       ' world!!!', ' morning!!!', ' are you?!!!'}
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