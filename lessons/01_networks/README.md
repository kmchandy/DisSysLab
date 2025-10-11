# 🧩 Lesson 1 Networks, blocks and connections


## 🎯 Goal


- Learn how to build a distributed application by creating a **network** which is **directed graph** in which nodes are **agents** that process messages and edges are channels along which messages flow.
---

## 💻 Example
 
```
# lessons.01_networks.basic_network.py

from dsl import network

def from_list():
    for item in ["hello", "world"]:
        yield item

def uppercase(v):
    return v.upper()

results = []

def to_results(x):
    results.append(x)


g = network([(from_list, uppercase), (uppercase, to_results)])

g.run_network()
print(results)  # Output: ['HELLO', 'WORLD']

```
## 📍 Network
A network is specified by the list of edges of a directed graph. An edge is an ordered pair **(u, v)** which is an edge from node **u** to node **v**. Every node of the network has at least one incident edge. The nodes of the network are the nodes that appear in the list of edges.

This example has two edges: ```(from_list, uppercase)``` and ```(uppercase, to_results)``` and  3 nodes: ```from_list```, ```upper_case```, and ```to_results```. The name of a node is the name of the function executed by the node. 

The node ```from_list``` is a **source**. A source function has no parameters. A source function is an iterator which generates a sequence of values. Each execution of **yield** generates another value. In this example the iterator ```from_list``` yields two values: "hello" and "world".

The node ```upper_case``` is a **transformer**. A transformer function has a single parameter and returns a single value.  In this example, the function ```upper_case``` has a single parameter ```v``` and returns a single value ```v.upper()```.

The node ```to_results``` is a **sink**. A sink function has a single parameter. The function ```to_results``` has a single parameter ```x``` and execution of the function appends ```x``` to the list ```results```.

A source has no input edges and has at least one output edge. A transformer node has at least one input edge and a least one output edge. A sink node has no output edges and at least one input edge.

## Edges
The graph has the two edges ```(from_list, upper_case)``` and from the node ```from_list``` to the node

## 📍 Example

We’ll create a :

1. **Source** – generate a stream of messages.
2. **Transform** – receive a message stream and output a transformation of the stream.
3. **Sink** – store or display a message stream. 

**Visual:** `[ Source ] → [ Transform ] → [ Sink ]`

---

## ⚙️ How It Works

- **🔲 Blocks**  
  - A block has sets of input  and output ports called **inports** and **outports**, respectively
  - A block executes a function that receives messages from its inports and sends messages through its outports.

- **🔗 Connections**  
  - A connection connects a block’s **output port** to a block’s **input port**. 


**Blocks in this example:**
- block name: **"source"**, 
  - execution: **FromList["hello", "world"]** – Generate a stream consisting of message "hello" followed by message "world". The stream is sent on an outport "out".
- block name: **"upper_case"**, 
  - execution: **Uppercase** – Receives a stream of messages on inport "in" and sends the uppercase of the messages that it receives on outport "out".
- block name: **"sink"**, 
  - execution: **ToList** – Receives a stream of messages on inport "in" and stores the stream that it receives in a list.

Block types with multiple inports and outports, and network structures that are not linear, are introduced later. 



---





## 🧠 Key Takeaways

- **network = blocks + connections**  
- **blocks**: each block executes a function that *processes messages*
- **connections**:  specify how *messages flow* from block to block.

### To do X, use function Y

- **Source** To generate a stream from a list or a file,.. use functions beginning with "From" such as `FromList([...])`, `FromFile(..)`
- **Transform** To receive a stream and output a computation of the stream use functions such as `Uppercase()`, `AddSentiment`, `ExtractEntities`
- **Sink** To record a stream to the console, or a list, or file use functions beginning with "To" such as `ToConsole()`, `ToList()`, `ToFile`
  
> See `dsl/kit/README_HowTo.md`.

---

### 🚀 Coming Up

Create a network that receives movie reviews, gives each movie a score by analyzing its review, and outputs both the review and its score.

👉 [**Next up: Chapter 2. Messages as Dictionaries.**](../02_msg_as_dict/README.md)
