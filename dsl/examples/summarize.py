from dsl.core import Network
from dsl.block_lib.stream_generators import generate
from dsl.block_lib.stream_transformers import SummarizeWithGPT
from dsl.block_lib.stream_recorders import RecordToList

results = []

net = Network(
    blocks={
        "gen": generate(["DisSysLab is a message-passing framework ..."], key="text"),
        "xf": SummarizeWithGPT(input_key="text"),
        "rec": RecordToList(results),
    },
    connections=[("gen", "out", "xf", "in"), ("xf", "out", "rec", "in")],
)

net.compile_and_run()
print(results)  # e.g., ["DisSysLab is a message-passing framework."]
