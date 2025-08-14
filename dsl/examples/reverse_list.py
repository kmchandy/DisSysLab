from dsl.core import Network
from dsl.block_lib.stream_generators import GenerateFromList
from dsl.block_lib.stream_transformers import TransformerFunction
from dsl.block_lib.stream_recorders import RecordToList


def reverse_text(x): return x[::-1]


results = []

net = Network(
    blocks={
        "generate_from_list": GenerateFromList(list=["abc", "def"]),
        "transform_msg": TransformerFunction(func=reverse_text),
        "record_to_list": RecordToList(results),
    },
    connections=[
        ("generate_from_list", "out", "transform_msg", "in"),
        ("transform_msg", "out", "record_to_list", "in")
    ]
)

net.compile_and_run()
# [{'data': 'abc', 'reversed': 'cba'}, {'data': 'def', 'reversed': 'fed'}]
print(results)
