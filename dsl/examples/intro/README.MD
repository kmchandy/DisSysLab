# 📘 Put Blocks Together: Build Your First Distributed Application

These short examples introduce ideas underlying DisSysLab, a framework for building
Python distributed applications. The central idea is that of a *block* an object 
with lists of input and output ports. A block sends messages on its output ports and
receives messages on its input ports. A network is a set of blocks and connections.
A connection is a 4-tuple (from_block, from_port, to_block, to_port) which specifies
that messages sent by from_block on from_port are received by to_block on to_port.

Some network structures, such as *pipelines*, can be specified without listing connections.
A network is itself a block. You can build networks of networks. An atomic block is specified
by a function that receives and sends messages. By convention,if a block has a single output 
port then that port is called "out". Likewise if a block has a single input port then that 
port is called "in".

A pipeline is a sequence of blocks where the first block in the sequence generates messages 
that it sends on its only output port. The last block receives messages on its only input 
port and records them. Intermediate blocks transform messages that it receives. A structure is
     [ generate ] ---> [ transform ] ---> .... ---> [ transform ] --->  [ record ]

Each example in this file has two views:
- ✅ **Block-and-Connection View** — explicitly shows each block and each connection.
- 🚀 **Pipeline View** — Uses the `pipeline(...)` helper function to specify a pipeline.
Examples in other files show other network structures and show networks with blocks that are
themselves networks.

In these examples, draw() is a function that shows a schematic of a network. It is optional.

To run these examples, paste the code into a Python script or Jupyter notebook. Make sure 
that you’ve installed required packages and activated your virtual environment.

---

## 🟢 Example 1: Convert Text to Uppercase

✅ Block-and-Connection View

```python
from dsl.core import Network
from dsl.block_lib.stream_generators import generate
from dsl.block_lib.stream_transformers import transform
from dsl.block_lib.stream_recorders import record
from dsl.visualize import draw

net = Network(
    blocks={
        "source": generate(["hello", "world"]),
        "uppercase": transform(str.upper),
        "sink": record()
    },
    connections=[
        ("source", "out", "uppercase", "in"),
        ("uppercase", "out", "sink", "in")
    ]
)

net.compile_and_run()
draw(net)
print("Output:", net.blocks["sink"].saved)
🚀 Pipeline View

from dsl.block_lib.graph_structures import pipeline
from dsl.block_lib.stream_generators import generate
from dsl.block_lib.stream_transformers import transform
from dsl.block_lib.stream_recorders import record
from dsl.visualize import draw

net = pipeline({
    "source": generate(["hello", "world"]),
    "uppercase": transform(str.upper),
    "sink": record()
})

net.compile_and_run()
draw(net)
print("Output:", net.blocks["sink"].saved)
🧠 What You Learned

A generate(...) block emits messages.

A transform(...) block modifies each message.

A record(...) block stores results.

You can define networks either as a graph or as a pipeline.


✨ Example 2: Reverse Each Word

net = pipeline({
    "source": generate(["distripy", "rocks"]),
    "reverse": transform(lambda s: s[::-1]),
    "sink": record()
})

net.compile_and_run()
print("Output:", net.blocks["sink"].saved)


🔢 Example 3: Square Numbers with NumPy

import numpy as np

net = pipeline({
    "source": generate([1, 2, 3]),
    "square": transform(np.square),
    "sink": record()
})

net.compile_and_run()
print("Output:", net.blocks["sink"].saved)


🤖 Example 4: Sentiment Analysis with GPT
python
Copy
Edit
from dsl.block_lib.stream_transformers import SentimentClassifierWithGPT

net = pipeline({
    "source": generate(["I love this!", "I hate waiting."]),
    "sentiment": SentimentClassifierWithGPT(),
    "sink": record()
})

net.compile_and_run()
print("Sentiment Labels:", net.blocks["sink"].saved)


🎭 Example 5: Merge Two Streams (Fan-In)

from dsl.core import Network
from dsl.block_lib.stream_transformers import TransformMultipleStreams

net = Network(
    blocks={
        "greetings": generate(["hi", "hello"]),
        "names": generate(["Alice", "Bob"]),
        "merge": TransformMultipleStreams(["a", "b"], lambda p: f"{p[0]}, {p[1]}!"),
        "sink": record()
    },
    connections=[
        ("greetings", "out", "merge", "a"),
        ("names", "out", "merge", "b"),
        ("merge", "out", "sink", "in")
    ]
)

net.compile_and_run()
print("Output:", net.blocks["sink"].saved)


💬 Example 6: Chat with GPT

from dsl.block_lib.stream_transformers import PromptToBlock

net = pipeline({
    "input": generate(["What's the capital of France?"]),
    "chat": PromptToBlock("Answer this: {msg}"),
    "sink": record()
})

net.compile_and_run()
print("GPT Says:", net.blocks["sink"].saved[0])

🧠 Summary
Connect blocks to build distributed systems.

Leverage commonly used network structures such as pipelines.

📚 What’s Next?
Explore more complex examples in:

dsl/examples/fan_in/ — multiple sources into one transformer

dsl/examples/fan_out/ — one source into multiple transformers

dsl/examples/star/ — central node connected to many others

dsl/examples/nested_networks - networks of networks

dsl/examples/gpt/ — language model integration

👉 Want to search by tags or keywords? We’ll be adding a natural language search soon!

