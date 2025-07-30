# 📘 Build Distributed Applications by Connecting Blocks

The goal of this set of examples is to show you how to specify a network as a dictionary (`dict`) blocks and a list of connections. The keys and values in the block dictionary are names of blocks and their specifications, respectively. A connection is a 4-tuple `(from_block, from_port, to_block, to_port)` which specifies that messages sent by `from_block` on `from_port` are received by `to_block` on `to_port`.

The first example also shows how to create a diagram showing connections by calling `draw`. The example uses the Agent class and types (sub-classes) of Agents called `generator`, `transform`, and `record`. A generate block has a single outport (short for "output port"), a transform block has a single inport and a single outport, and a record block has a single inport. By convention, a single outport is called "out" and a single inport is called "in". 

### generate
A generate block is specified by a list or a Python generator; the generate block sends messages from the specified list or function on its outport. 

Examples:
- `generate(["hello", "world"])'
- 

### transform
A transform block is specified by a function; it applies the function to messages it receives on its inport and sends the results on its outports.

### transform
 and it sends messages on its output port. A transform block has a single input port and a single output port; it applies a function to messages it receives on its input port and sends results on its output port. 

A generate block is specified by the list or Python generator function that it wraps. A

---

## 🟢 Example 1: Convert Text to Uppercase

### Block and Connection Specification
```python
from dsl.core import Network
from dsl.block_lib.stream_generators import generate
from dsl.block_lib.stream_transformers import transform
from dsl.block_lib.stream_recorders import record
from dsl.utils.visualize import draw

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
from dsl.utils.visualize import draw

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
from dsl.utils.visualize import draw

net = Network(
    blocks={
        "generate_words": generate(["AI", "is", "now"]),
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
from dsl.utils.visualize import draw

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
# Convert np.int to int
print(f"Output:, {[int(v) for v in net.blocks['sink'].saved]}")
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
# Convert np.int to int
print(f"Output:, {[int(v) for v in net.blocks['sink'].saved]}")
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
print("Sentiment Labels:", net.blocks['sink'].saved)
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
print("Sentiment Labels:", net.blocks['sink'].saved)
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