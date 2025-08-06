from dsl.core import Network
from dsl.block_lib.stream_generators import generate
from dsl.block_lib.stream_transformers import ExtractEntitiesWithGPT
from dsl.block_lib.stream_recorders import RecordToList

results = []

net = Network(
    blocks={
        "gen": generate(["Barack Obama was president"], key="text"),
        "xf": ExtractEntitiesWithGPT(input_key="text"),
        "rec": RecordToList(results),
    },
    connections=[("gen", "out", "xf", "in"), ("xf", "out", "rec", "in")],
)

net.compile_and_run()
print(results)  # e.g., [["Barack Obama"]]
