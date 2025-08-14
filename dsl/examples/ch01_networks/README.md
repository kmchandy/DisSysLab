# 🧩 Step 1 — Networks = Blocks + Connections

### 🎯 Goal
Learn how to build a distributed application in **DisSysLab** by creating **blocks** and connecting them to form a **network**.

---

## 📍 1. What We’ll Build

We’ll create a **three-block network**:

1. **Generator** – produces a list of short text strings.  
2. **Transformer** – applies a function to each string (in this case, reversing the text).  
3. **Recorder** – saves the results in a Python list.

**Visual:** `[ Generator ] → [ Transformer ] → [ Recorder ]`

---

## ⚙️ 2. How It Works

- **🔲 Blocks**  
  - Can have **zero or more input ports** and **zero or more output ports**.  
  - Run a **function** to generate, transform, or record messages.

- **🔗 Connections**  
  - Link one block’s **output port** to another block’s **input port**.  
  - In this chapter, all messages are plain strings (e.g., `"abc"`, `"def"`).

**Block types in this example:**
- **Generator** – single outport, no inports.  
- **Transformer** – single inport, single outport.  
- **Recorder** – single inport, no outports.

Block types with multiple inports and outports are introduced later.

---

## 💻 3. Code Example

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

# Define the network
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

# Display the results
print(results)  # ['cba', 'fed']

python3 -m dsl.examples.ch01_networks.simple_network

['cba', 'fed']
```

## 🧠 5. Key Takeaways

- **A network = blocks + connections**  
  Blocks define *functions* that process messages; connections define the *flow of messages*.