from dsl.core import Network
from dsl.block_lib.stream_generators import generate
from dsl.block_lib.stream_transformers import SentimentClassifierWithGPT
from dsl.block_lib.stream_recorders import RecordToList

results = []

net = Network(
    blocks={
        "gen": generate(["I love pizza", "I hate waiting"], key="text"),
        "clf": SentimentClassifierWithGPT(input_key="text"),
        "rec": RecordToList(results),
    },
    connections=[("gen", "out", "clf", "in"), ("clf", "out", "rec", "in")]
)

net.compile_and_run()
print(results)  # e.g., ["Positive", "Negative"]
