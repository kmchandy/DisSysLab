from dsl.core import Network
from dsl.block_lib.stream_generators import GenerateFromList
from dsl.block_lib.stream_transformers import TransformerFunction
from dsl.block_lib.stream_recorders import RecordToList


def reverse_text(x): return x[::-1]


results = []
net = Network(
    blocks={
        "generate_from_list": GenerateFromList(items=["abc", "def"]),
        "reverse_msg": TransformerFunction(func=reverse_text),
        "record_to_list": RecordToList(results),
    },
    connections=[
        ("generate_from_list", "out", "reverse_msg", "in"),
        ("reverse_msg", "out", "record_to_list", "in")
    ]
)

net.compile_and_run()
print(results)  # ['cba', 'fed']
