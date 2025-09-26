# dsl.examples.simple_entity_extractor

from dsl import Graph
from dsl.ops.transforms.simple_entity_extractor import extract_entity

# -----------------------------------------------------------
# Define Python functions independent of dsl.
# -----------------------------------------------------------


def from_list(items):
    for x in items:
        yield x


def to_list(v, target):
    target.append(v)


messages = [
    {"text": "Obama was the President of the USA."},
    {"text": "Charles is the King of the UK."},
]

# -----------------------------------------------------------
# Define the graph
# -----------------------------------------------------------
results = []

g = Graph(
    edges=[("src_0", "trn_0"), ("trn_0", "snk")],
    nodes={
        "src_0": (from_list, {"items": messages}),
        "trn_0": (extract_entity, {}),
        "snk": (to_list, {"target": results}),
    },
)
# -----------------------------------------------------------

g.compile_and_run()
if __name__ == "__main__":
    for result in results:
        print(result)
