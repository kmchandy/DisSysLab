<!-- modules/agents/README.md  -->

# Module 3: Agents with input and output ports

## Key Point
This module introduces a type of node called **Split** which has a single input and two or more outputs along which it sends messages.

The module also shows how to build systems with agents that may have multiple named input and output ports. Edges of the system network are connected explicitly to ports of agents.


## Naming Convention
In the previous module we described nodes in a graph representation of a distributed system. The nodes are sources, transformers or sinks. 

A source has exactly one output port which is called "out" and has no input ports. A sink has exactly one input port which is called "in" and has no output ports. A transformer has exactly one input port and exactly one output port which are called "in" and "out" respectively. An edge of the graph is from an output port of a node to an input port of a node. You can (though you don't have to) specify ports explicitly in edges between sources, sinks and transformers. The following are equivalent ways of specifying edges:
```python
(v.out, w.in)
(v, w.in)
(v.out, w)
(v, w)
```


A split with n > 1 outputs has a single input port called "in" and n output ports called "out_k", for 0 <= k <n.

You can specify arbitrary names for ports of agents.

## Split
Split is specified by **Split(fn=f, num_outputs=n)** where n is an integer greater than 1 and f is a function that takes a single argument and returns a list of length n. When a message arrives at a split node, function f is passed the message as its argument, and the k-th element of the list returned by f is sent as a message along the k-th output port, i.e. "out_k".

Lets look at a simple example:
```python
# function that returns lists of length 2
def f(msg):
    if msg % 2 == 0:
        return [msg, None]
    else:
        return [None, msg]

# Split 2 ways
odd_even_split = Split(fn=f, num_outputs=2)
```
odd_even_split sends even numbers that it receives on output port "out_0", and odd numbers on output port "out_1". A complete example is given next:

### Example: A simple two-way split
```python
# modules/agents/trivial_split.py

"""
Two way split
"""

from dsl.blocks import Source, Split, Sink
from dsl import network
from components.sources.natural_numbers_source import NaturalNumberGenerator


def f(msg):
    if msg % 2 == 0:
        return [msg, None]
    else:
        return [None, msg]


# Create source
num_gen = NaturalNumberGenerator(max_count=10)
source = Source(num_gen.run)

# num_outputs must be specified for splitter
odd_even_split = Split(fn=f, num_outputs=2)

# Make sinks
odds, evens = [], []
def append_to_odds(msg): odds.append(msg)
def append_to_evens(msg): evens.append(msg)


# Build network topology
g = network([
    (source, odd_even_split),
    (odd_even_split, "out_0", Sink(append_to_evens)),
    (odd_even_split, "out_1", Sink(append_to_odds)),
])

# Run the Network

if __name__ == "__main__":
    g.run_network()
    print("Evens:", evens)
    print("Odds:", odds)
```
You can run the program from the root DisSysLab directory by executing
```python
python -m modules.agents.trivial_split
```

# Example: A Round-Robin Split
Next let's look at a split that sends messages on its output ports in a round-robin fashion.
```python

from dsl.blocks import Source, Split, Sink
from dsl import network
from components.sinks.sink_simple_file import FileLineWriter
from components.sources.natural_numbers_source import NaturalNumberGenerator

class RoundRobinRouter:
    """Routes messages round-robin across N outputs"""

    def __init__(self, num_outputs=3):
        self.num_outputs = num_outputs
        self.counter = 0

    def run(self, msg):
        """
        Route message to one output based on counter.
        Returns list of N messages where only one is non-None.
        """
        # Create result list with None for all positions
        results = [None] * self.num_outputs

        # Put message at current position
        output_index = self.counter % self.num_outputs
        results[output_index] = msg

        # Increment counter for next message
        self.counter += 1

        return results


# Build the Network

# Create source
num_gen = NaturalNumberGenerator(max_count=10)
source = Source(num_gen.run)

# Create split with round-robin router
router = RoundRobinRouter(3)
# num_outputs must be specified for splitter
splitter = Split(fn=router.run, num_outputs=3)

# Create three file writer sinks
writer0 = FileLineWriter("file_0.txt")
writer1 = FileLineWriter("file_1.txt")
writer2 = FileLineWriter("file_2.txt")

sink0 = Sink(writer0.run)
sink1 = Sink(writer1.run)
sink2 = Sink(writer2.run)

# Build network topology
g = network([
    (source, splitter),
    (splitter, "out_0", sink0),
    (splitter, "out_1", sink1),
    (splitter, "out_2", sink2),
])

g.run_network()

```