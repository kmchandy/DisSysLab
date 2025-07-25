# 📘 Put Blocks Together: Build Your First Distributed Application

These short examples introduce ideas underlying DisSysLab, a framework for building
Python distributed applications. The central idea is that of a *block* — an object 
with lists of input and output ports. A block sends messages on its output ports and
receives messages on its input ports. A network is a set of blocks and connections.
A connection is a 4-tuple `(from_block, from_port, to_block, to_port)` which specifies
that messages sent by `from_block` on `from_port` are received by `to_block` on `to_port`.

Some network structures, such as *pipelines*, can be specified without listing connections.
A network is itself a block. You can build networks of networks. An atomic block is specified
by a function that receives and sends messages. By convention, if a block has a single output 
port then that port is called `"out"`. Likewise, if a block has a single input port then that 
port is called `"in"`.

A pipeline is a sequence of blocks:  
`[ generate ] ---> [ transform ] ---> ... ---> [ transform ] ---> [ record ]`

Each example has two Specifications:
- ✅ **Block and Connection Specification** — explicitly shows each block and connection
- 🚀 **Pipeline Specification** — uses the `pipeline({...})` helper for simplicity

You may run these examples in a script or Jupyter notebook. Make sure your environment is active.

---

## 🟢 Example 1: Convert Text to Uppercase

### Block and Connection Specification
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
```
### 🚀 Pipeline Specification

```python
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
```

## 🟢 Example 2: Reverse Each Word in a List
### Block and Connection Specification

```python
from dsl.core import Network
from dsl.block_lib.stream_generators import generate
from dsl.block_lib.stream_transformers import transform
from dsl.block_lib.stream_recorders import record
from dsl.visualize import draw

net = Network(
    blocks={
        "generate_words": generate(["AI", "is", "amazing"]),
        "reverse": transform(lambda s: s[::-1]),
        "sink": record()
    },
    connections=[
        ("generate_words", "out", "reverse", "in"),
        ("reverse", "out", "sink", "in")
    ]
)

net.compile_and_run()
draw(net)
print("Output:", net.blocks["sink"].saved)
```


### 🚀 Pipeline Specification
```python
from dsl.block_lib.graph_structures import pipeline
from dsl.block_lib.stream_generators import generate
from dsl.block_lib.stream_transformers import transform
from dsl.block_lib.stream_recorders import record
from dsl.visualize import draw

net = pipeline({
    "generate_words": generate(["AI", "is", "amazing"]),
    "reverse": transform(lambda s: s[::-1]),
    "sink": record()
})

net.compile_and_run()
draw(net)
print("Output:", net.blocks["sink"].saved)
```

## 🔢 Example 3: Square Numbers Using NumPy

### Block and Connection Specification
```python

import numpy as np
from dsl.core import Network
from dsl.block_lib.stream_generators import generate
from dsl.block_lib.stream_transformers import transform
from dsl.block_lib.stream_recorders import record

net = Network(
    blocks={
        "generate_numbers": generate([1, 2, 3]),
        "square": transform(np.square),
        "sink": record()
    },
    connections=[
        ("generate_numbers", "out", "square", "in"),
        ("square", "out", "sink", "in")
    ]
)

net.compile_and_run()
print("Output:", net.blocks["sink"].saved)
```

### 🚀 Pipeline Specification

```python
import numpy as np
from dsl.block_lib.graph_structures import pipeline
from dsl.block_lib.stream_generators import generate
from dsl.block_lib.stream_transformers import transform
from dsl.block_lib.stream_recorders import record

net = pipeline({
    "generate_numbers": generate([1, 2, 3]),
    "square": transform(np.square),
    "sink": record()
})

net.compile_and_run()
print("Output:", net.blocks["sink"].saved)
```

## 🤖 Example 4: Sentiment Analysis with GPT

### Block and Connection Specification
```python
from dsl.core import Network
from dsl.block_lib.stream_generators import generate
from dsl.block_lib.stream_transformers import SentimentClassifierWithGPT
from dsl.block_lib.stream_recorders import record

net = Network(
    blocks={
        "source": generate(["I love this!", "I hate waiting."]),
        "sentiment": SentimentClassifierWithGPT(),
        "sink": record()
    },
    connections=[
        ("source", "out", "sentiment", "in"),
        ("sentiment", "out", "sink", "in")
    ]
)

net.compile_and_run()
print("Sentiment Labels:", net.blocks["sink"].saved)
```

### 🚀 Pipeline Specification

```python
from dsl.block_lib.graph_structures import pipeline
from dsl.block_lib.stream_generators import generate
from dsl.block_lib.stream_transformers import SentimentClassifierWithGPT
from dsl.block_lib.stream_recorders import record

net = pipeline({
    "source": generate(["I love this!", "I hate waiting."]),
    "sentiment": SentimentClassifierWithGPT(),
    "sink": record()
})

net.compile_and_run()
print("Sentiment Labels:", net.blocks["sink"].saved)
```

## 💬 Example 5: Chat with GPT

### Block and Connection Specification
```python
from dsl.core import Network
from dsl.block_lib.stream_generators import generate
from dsl.block_lib.stream_transformers import PromptToBlock
from dsl.block_lib.stream_recorders import record

net = Network(
    blocks={
        "source": generate(["What's the capital of France?"]),
        "chat": PromptToBlock("Answer this: {msg}"),
        "sink": record()
    },
    connections=[
        ("source", "out", "chat", "in"),
        ("chat", "out", "sink", "in")
    ]
)

net.compile_and_run()
print("GPT Says:", net.blocks["sink"].saved[0])
```

### 🚀 Pipeline Specification
```python

from dsl.block_lib.graph_structures import pipeline
from dsl.block_lib.stream_generators import generate
from dsl.block_lib.stream_transformers import PromptToBlock
from dsl.block_lib.stream_recorders import record

net = pipeline({
    "input": generate(["What's the capital of France?"]),
    "chat": PromptToBlock("Answer this: {msg}"),
    "sink": record()
})

net.compile_and_run()
print("GPT Says:", net.blocks["sink"].saved[0])
```

## 🎭 Example 6: Merge Two Streams (Fan-In)

### Block and Connection Specification
```python

from dsl.core import Network
from dsl.block_lib.stream_generators import generate
from dsl.block_lib.stream_transformers import TransformMultipleStreams
from dsl.block_lib.stream_recorders import record

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
```

## 🧠 Summary
generate(...) emits a stream of values

transform(...) modifies each value

record(...) captures results

You can define pipelines or general networks

Use GPT-based transformers for LLM-powered tasks

Wrap functions from NumPy, SciKit and other libraries into blocks.

## 📚 What’s Next?
Explore:

dsl/examples/fan_in/ — multiple sources into one block

dsl/examples/fan_out/ — one source into multiple blocks

dsl/examples/star/ — central hub structure

dsl/examples/gpt/ — integrating large language models

dsl/examples/nested_networks/ — build networks of networks

👉 Coming Soon: Natural Language Search for Examples