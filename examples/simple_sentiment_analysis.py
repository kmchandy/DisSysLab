# dsl.examples.simple_sentiment_analysis

from dsl import Graph
from dsl.ops.transforms.simple_sentiment import add_sentiment

# -----------------------------------------------------------
# Define Python functions independent of dsl.
# -----------------------------------------------------------


def from_list_with_key(items, key):
    for x in items:
        yield {key: x}


def to_list(v, target):
    target.append(v)


reviews = [
    "The movie was great. The music was superb!",
    "The concert was terrible. I hated the performance.",
    "The book was okay, not too bad but not great either.",
    "This is the best course on AI I've ever taken!",
]

# -----------------------------------------------------------
# Define the graph
# -----------------------------------------------------------
results = []

g = Graph(
    edges=[("src_0", "trn_0"), ("trn_0", "snk")],
    nodes={
        "src_0": (from_list_with_key, {"items": reviews, "key": "review"}),
        "trn_0": (add_sentiment, {"input_key": "review"}),
        "snk": (to_list, {"target": results}),
    },
)
# -----------------------------------------------------------

g.compile_and_run()
if __name__ == "__main__":
    for result in results:
        print(result)
