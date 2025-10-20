## 🧩 1.5 Termination


## 🎯 Goal


- Sending termination messages and terminating agents.

---

## 💻 Example: Sending termination messages
 
```python
 # lessons.01_networks.stop_example

from dsl import network
import time

def from_list_0():
    for item in ["a", "b"]:
        yield item
        time.sleep(0.06)
    # When this generator finishes, the FRAMEWORK emits STOP downstream.

def from_list_1():
    for item in ["u", "v", "w", "x", "y", "z"]:
        yield item
        time.sleep(0.03)
    # When this generator finishes, the FRAMEWORK emits STOP downstream.

def uppercase(x):
    return x.upper()
    # The framework delivers STOP to this node once all inputs have stopped,
    # then propagates STOP after pending items are processed.

results_0 = []
def to_results_0(v):
    results_0.append(v)
    # The sink terminates after it receives STOP on all inputs.

results_1 = []
def to_results_1(v):
    results_1.append(v)
    # The sink terminates after it receives STOP on all inputs.

g = network([
    (from_list_0, uppercase),
    (from_list_1, uppercase),
    (uppercase, to_results_0),
    (uppercase, to_results_1),
])
g.run_network()

# Order is nondeterministic; both sinks receive the same multiset of items.
assert set(results_0) == {"A", "B", "U", "V", "W", "X", "Y", "Z"}
assert set(results_1) == {"A", "B", "U", "V", "W", "X", "Y", "Z"}

```
## 📍 Termination and Stop Signals

- A source terminates when its iterator is exhausted. The framework then emits a stop signal downstream. Some sources (e.g., news feeds, sensors) may never terminate.

- A transformer terminates after it receives a stop signal on each of its inputs; then the framework propagates a stop signal to its outputs.

- A sink terminates after it receives a stop signal on each of its inputs.

- The entire network terminates when all agents have terminated and channels are empty.

About cycles: This lesson describes the acyclic case. Termination detection for networks with cycles comes later.

Note: The framework’s stop signal (e.g., "__STOP__") is managed by the runtime. Do not yield or pass STOP yourself.


### The Example
In this example, the node ```from_list_0``` sends a stop signal and terminates execution after sending "a" and then "b". Likewise, ```from_list_1``` sends a stop signal and terminates execution after sending "u", "v", "w", "x", "y", and "z". Node ```uppercase``` terminates execution and sends a stop signal after it receives the stop signals from both ```from_list_0``` and ```from_list_1```. The stop signal from ```uppercase``` is broadcast to both ```to_results_0``` and ```to_results_1``` which terminate execution when they receive the signal.

The stop signal used in these examples is "__STOP__" and you can change it in ```DisSysLab.dsl.core```.

## 🧠 Key Concepts
- The runtime handles stop propagation; user code just finishes/returns.

- Acyclic networks terminate when every node has received/propagated STOP.

- Algorithms for termination detection of cyclic networks are given later.