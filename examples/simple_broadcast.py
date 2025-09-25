# dsl.examples.graph_pipeline

from dsl import Graph

# -----------------------------------------------------------
# Define Python functions independent of dsl.
# -----------------------------------------------------------


def from_list(items):
    for item in items:
        yield item


def to_list(v, target):
    target.append(v)


# -----------------------------------------------------------
# Define the graph
# -----------------------------------------------------------
results_0 = []
results_1 = []
g = Graph(
    edges=[("src", "snk_0"), ("src", "snk_1")],
    nodes={
        "src": (from_list, {"items": ["hello", "world"]}),
        "snk_0": (to_list,   {"target": results_0}),
        "snk_1": (to_list,   {"target": results_1}),
    },
)
# -----------------------------------------------------------

g.compile_and_run()

if __name__ == "__main__":
    assert results_0 == ['hello', 'world']
    assert results_1 == ['hello', 'world']
