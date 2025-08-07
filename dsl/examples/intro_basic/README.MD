# 📘 Build Distributed Applications by Connecting Blocks

These examples show you how to build a distributed application as a network consisting of connected blocks.

 The blocks in a network are specified as a dictionary (`dict`). A key of the dict is the name of a block and the value is the corresponding specification of the block. 
 
 A connection is a 4-tuple `(from_block, from_port, to_block, to_port)` which specifies that messages sent by block `from_block` on port `from_port` are received by block `to_block` on port `to_port`.

---

## 🟢 Example 1: Convert Text to Uppercase

### Block and Connection Specification
```python
def illustrate_blocks_and_connections_1():
    results = []

    net = Network(
        blocks={
            "gen": generate(["abc", "def"]),
            "tran": StreamTransformer(transform_fn=reverse_text),
            "rec": RecordToList(results),
        },
        connections=[
            ("gen", "out", "tran", "in"),
            ("tran", "out", "rec", "in")
        ],
    )

    net.compile_and_run()
    assert results == ["cba", "fed"]
```
This example has three blocks called "gen", "tran" and "rec". The block called "gen" is specified by:
```generate(["abc", "def"])```. We describe how blocks are specified later.



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