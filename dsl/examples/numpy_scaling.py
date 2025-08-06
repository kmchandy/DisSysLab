import numpy as np
from sklearn.preprocessing import MinMaxScaler
from dsl.core import Network
from dsl.block_lib.stream_generators import generate
from dsl.block_lib.stream_transformers import WrapFunction
from dsl.block_lib.stream_recorders import RecordToList

scaler = MinMaxScaler()
scaler.fit([[1], [2], [3]])

def scale(x): return scaler.transform([[x]])[0][0]

results = []

net = Network(
    blocks={
        "gen": generate([1, 2, 3], key="x"),
        "scale": WrapFunction(func=scale, input_key="x", output_key="scaled"),
        "rec": RecordToList(results)
    },
    connections=[("gen", "out", "scale", "in"), ("scale", "out", "rec", "in")]
)

net.compile_and_run()
print(results)  # [{'x': 1, 'scaled': 0.0}, {'x': 2, 'scaled': 0.5}, {'x': 3, 'scaled': 1.0}]
