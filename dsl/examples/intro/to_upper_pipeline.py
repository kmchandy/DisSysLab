from dsl.core import Network
from dsl.block_lib.stream_generators import generate
from dsl.block_lib.stream_transformers import transform
from dsl.block_lib.stream_recorders import record
from dsl.visualize import draw
from dsl.utils.graph_structures import pipeline


# --------------------------------------------------
# Version 1: Using explicit blocks and connections
# --------------------------------------------------

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

print("--- Block and Connection View ---")
net.compile_and_run()
draw(net)
print("Recorded output:", net.blocks["sink"].saved)


# --------------------------------------------------
# Version 2: Using pipeline convenience helper
# --------------------------------------------------

net2 = pipeline([
    generate(["hello", "world"]),
    transform(str.upper),
    record()
])

print("\n--- Pipeline View ---")
net2.compile_and_run()
draw(net2)
print("Recorded output:", net2.blocks["block_2"].saved)  # The third block
