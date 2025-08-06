from dsl.core import Network
from dsl.block_lib.stream_generators import generate
from dsl.block_lib.stream_transformers import WrapFunction
from dsl.block_lib.stream_recorders import RecordToList

def reverse_text(x): return x[::-1]

results = []

net = Network(
    blocks={
        "gen": generate(["abc", "def"], key="data"),
        "rev": WrapFunction(func=reverse_text, input_key="data", output_key="reversed"),
        "rec": RecordToList(results),
    },
    connections=[("gen", "out", "rev", "in"), ("rev", "out", "rec", "in")]
)

net.compile_and_run()
print(results)  # [{'data': 'abc', 'reversed': 'cba'}, {'data': 'def', 'reversed': 'fed'}]
