# dsl/examples/chXX_stream/cockpit_demo.py
from dsl.core import Network
from dsl.block_lib.stream_generators import GenerateFromList
from dsl.block_lib.stream_transformers import TransformerFunction
from dsl.connector_lib.outputs import BatchOutput, ConsoleFlushPrinter


def to_row(msg):
    return {"row": f"- {msg.get('text', '(no text)')}"}


net = Network(
    blocks={
        "gen": GenerateFromList(items=[{"text": f"tick {i}"} for i in range(100)], delay=0.01),
        "row": TransformerFunction(func=to_row),
        "batch": BatchOutput(N=25, meta_builder=lambda buf: {"title": "Cockpit Digest"}),
        # tweak sample size as you like
        "console": ConsoleFlushPrinter(sample_size=6),
    },
    connections=[
        ("gen", "out", "row", "in"),
        ("row", "out", "batch", "in"),
        ("batch", "out", "console", "in"),
    ],
)

if __name__ == "__main__":
    net.compile_and_run()
