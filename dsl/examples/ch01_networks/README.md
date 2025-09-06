# 🧩 Chapter 1 — Networks = Blocks + Connections

### 🎯 Goal
Learn how to build a distributed application by creating **blocks** and connecting them to form a **network**.

See an example of the two core ideas:

- A distributed system consists of connected blocks.
- A block embodies a function.

---

## 📍 What We’ll Build

We’ll create a **three-block network**:

1. **Generator** – produces a list of short text strings.  
2. **Transformer** – applies a function to each string (in this case, reversing the text).  
3. **Recorder** – saves the results in a Python list.

**Visual:** `[ Generator ] → [ Transformer ] → [ Recorder ]`

---

## ⚙️ How It Works

- **🔲 Blocks**  
  - A block has some number of input and output ports called inports and outports, respectively
  - A block executes a function that receives messages from its inports and sends messages through its outports.

- **🔗 Connections**  
  - A connection connects a block’s **output port** to a block’s **input port**. 

**📊 Diagram of blocks and connections of this example:**

![Simple Network](simple_network.svg)

**Blocks in this example:**
- **generate_from_list** – executes ```GenerateFromList(items=["abc", "def"])```. It is an example of a **Generator** block which has a single outport and no inports.  
- **reverse_msg** – executes ```TransformerFunction(func=reverse_text)``. It is an example of a **Transformer** block which has a  single inport and a single outport.  
- **record_to_list** – executes ```RecordToList(results)```. It is an example of a **Recorder** block which has a single inport and  no outports.

(Block types with multiple inports and outports are introduced later.)



---

## 💻 Code Example
 
```python
# dsl/examples/ch01_networks/simple_network.py

from dsl.core import Network
from dsl.block_lib.stream_generators import GenerateFromList
from dsl.block_lib.stream_transformers import TransformerFunction
from dsl.block_lib.stream_recorders import RecordToList

# Transformation function: reverse a string
def reverse_text(x):
    return x[::-1]

# Where we’ll store results
results = []

# Define the network: blocks and connections
# blocks is a dict where the key is the block name and 
# the value is the function executed by the block.
# connections is a list of 4-tuples 
#        (from_block_name, outport, to_block_name, inport)
net = Network(
    blocks={
        "generate_from_list": GenerateFromList(items=["abc", "def"]),
        "reverse_msg": TransformerFunction(func=reverse_text),
        "record_to_list": RecordToList(results),
    },
    connections=[
        ("generate_from_list", "out", "reverse_msg", "in"),
        ("reverse_msg", "out", "record_to_list", "in"),
    ]
)

# Run the network
net.compile_and_run()
```

### ▶️ Run It
```
python3 -m dsl.examples.ch01_networks.simple_network

['cba', 'fed']
```



## 🧠 Key Takeaways

- **network = blocks + connections**  
- **blocks**: each block executes a function that *processes messages*
- **connections**:  specify how *messages flow* from block to block.

---

### 🚀 Coming Up

Would you like to create a network that receives movie reviews, gives each movie a score by analyzing its review, and outputs both the review and its score?

👉 [**Next up: Chapter 2. Messages as Dictionaries.**](../ch02_keys/README.md)
