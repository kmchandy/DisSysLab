from dsl.block_lib.stream_recorders import RecordToList
from dsl.block_lib.stream_transformers import TransformerFunction
from dsl.block_lib.stream_generators import GenerateFromList
from dsl.core import Network

# dsl/examples/ch02_keys/reverse_example.py


# Transformation function: reverse a string

def reverse_text(x):
    return x[::-1]


results = []

net = Network(
    blocks={
        # Generator emits dicts: {"text": "abc"}, {"text": "def"}
        "generator": GenerateFromList(
            items=["abc", "def"],
            key="text"
        ),
        # Transformer reads msg["text"], writes msg["reversed"]
        "reverser": TransformerFunction(
            func=reverse_text,
            input_key="text",
            output_key="reversed",
        ),
        # Recorder saves the resulting dictionaries
        "recorder": RecordToList(results),
    },
    connections=[
        ("generator", "out", "reverser", "in"),
        ("reverser", "out", "recorder", "in"),
    ]
)

net.compile_and_run()
print(results)
