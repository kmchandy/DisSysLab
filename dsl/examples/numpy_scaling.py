from dsl.core import Network
from dsl.block_lib.stream_generators import generate
from dsl.block_lib.stream_transformers import WrapFunction
from dsl.block_lib.stream_recorders import RecordToList
import numpy as np


# NumPy min-max normalization
def minmax_scale(list_of_numbers):
    arr = np.array(list_of_numbers)
    min_val = arr.min()
    max_val = arr.max()
    if min_val == max_val:
        return [0.0 for _ in arr]  # avoid divide by zero
    return ((arr - min_val) / (max_val - min_val)).tolist()


results = []

net = Network(
    blocks={
        "gen": generate([
            [1, 2, 3],
            [10, 20, 30],
            [5, 5, 5],  # test edge case: constant values
        ], key="x"),
        "scale": WrapFunction(func=minmax_scale, input_key="x", output_key="scaled"),
        "rec": RecordToList(results),
    },
    connections=[("gen", "out", "scale", "in"), ("scale", "out", "rec", "in")]
)

net.compile_and_run()
print(results)
