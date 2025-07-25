from dsl.block_lib.stream_transformers import TransformMultipleStreams
from dsl.block_lib.stream_transformers import PromptToBlock
from dsl.block_lib.stream_transformers import SentimentClassifierWithGPT
import numpy as np
from dsl.core import Network
from dsl.block_lib.stream_generators import generate
from dsl.block_lib.stream_transformers import transform
from dsl.block_lib.stream_recorders import record
from dsl.utils.visualize import draw
from dsl.block_lib.graph_structures import pipeline


# -------------------------------------------------
# EXAMPLE 1: Convert Text to Uppercase
# -------------------------------------------------
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
print(f"Example 1: Convert Text to Uppercase \n")
print(f"Block and Connection Specification \n")
print("Output:", net.blocks["sink"].saved)
print(f"\n")

#  --------- pipeline ----------------
net = pipeline({
    "source": generate(["hello", "world"]),
    "uppercase": transform(str.upper),
    "sink": record()
})

net.compile_and_run()
print(f"Example 1: Output for Pipeline Specification \n")
print("Output:", net.blocks["sink"].saved)
print(f"\n \n")


# -------------------------------------------------
# EXAMPLE 2: Reverse Each Word in a List
# -------------------------------------------------

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
print(f"Example 2: Reverse Each Word in a List")
print(f"Output for block and connection specification")
print("Output:", net.blocks["sink"].saved)
print("\n")

#  --------- pipeline ----------------
net = pipeline({
    "generate_words": generate(["AI", "is", "now"]),
    "reverse": transform(lambda s: s[::-1]),
    "sink": record()
})

net.compile_and_run()
draw(net)
print(f"EXAMPLE 2: Output for Pipeline Specification")
print("Output:", net.blocks["sink"].saved)
print("\n \n")

# -------------------------------------------------
# EXAMPLE 3: Square Numbers Using NumPy
# -------------------------------------------------
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
print(f"Example 3: Square Numbers Using NumPy")
print(f"Output for block and connection specification")
print(f"Output: {[int(v) for v in net.blocks['sink'].saved]}")
print(f"\n")

#  --------- pipeline ----------------
net = pipeline({
    "generate_numbers": generate([1, 2, 3]),
    "square": transform(np.square),
    "sink": record()
})

net.compile_and_run()
print(f"EXAMPLE 3: Output for Pipeline Specification")
print(f"Output: {[int(v) for v in net.blocks['sink'].saved]}")
print(f"\n \n")

# -------------------------------------------------
# EXAMPLE 4: Sentiment Analysis with GPT
# -------------------------------------------------

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
print(f"Example 4: Sentiment Analysis with GPT")
print(f"Output for block and connection specification")
print(f"Sentiment Labels: {net.blocks['sink'].saved}")
print(f"\n")

#  --------- pipeline ----------------
net = pipeline({
    "source": generate(["I love this!", "I hate waiting."]),
    "sentiment": SentimentClassifierWithGPT(),
    "sink": record()
})

net.compile_and_run()
print(f"EXAMPLE 4: Output for Pipeline Specification")
print(f"Sentiment Labels: {net.blocks['sink'].saved}")
print(f"\n \n")

# -------------------------------------------------
# EXAMPLE 5: Chat with GPT
# -------------------------------------------------
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
print(f"Example 5: Chat with GPT")
print(f"Output for block and connection specification")
print("GPT Says:", net.blocks["sink"].saved[0])
print(f"\n")

#  --------- pipeline ----------------
net = pipeline({
    "input": generate(["What's the capital of France?"]),
    "chat": PromptToBlock("Answer this: {msg}"),
    "sink": record()
})

net.compile_and_run()
print(f"EXAMPLE 5: Output for Pipeline Specification")
print("GPT Says:", net.blocks["sink"].saved[0])

print(f"\n \n")

# -------------------------------------------------
# EXAMPLE 6: Merge Two Streams (Fan-In)
# -------------------------------------------------
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
print(f"Example 6: Merge Two Streams (Fan-In)")
print(f"Output for block and connection specification")
print("Output:", net.blocks["sink"].saved)
