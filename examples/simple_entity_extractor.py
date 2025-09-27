# dsl.examples.simple_entity_extractor

from dsl import Graph
from dsl.ops.transforms.simple_entity_extractor import extract_entity

# -----------------------------------------------------------
# Define Python functions independent of dsl.
# -----------------------------------------------------------


def src():
    for x in messages:
        yield x


def to_results(v):
    results.append(v)


messages = [
    {"text": "Obama was the President of the USA."},
    {"text": "Charles is the King of the UK."},
]

# -----------------------------------------------------------
# Define the graph
# -----------------------------------------------------------
results = []

g = Graph(
    edges=[("src", "trn"), ("trn", "snk")],
    nodes=[("src", src), ("trn", extract_entity), ("snk", to_results)]
)
# -----------------------------------------------------------

g.compile_and_run()
if __name__ == "__main__":
    for result in results:
        print(result)
