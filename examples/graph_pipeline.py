# dsl.examples.graph_pipeline

from dsl import Graph

# -----------------------------------------------------------
# Define Python functions independent of dsl.
# -----------------------------------------------------------


def from_list(items):
    for item in items:
        yield item


def add_suffix(v, suffix):
    return v + suffix


def to_list(v, target):
    target.append(v)


# -----------------------------------------------------------
# Define the graph
# -----------------------------------------------------------
results = []
g = Graph(
    edges=[("src", "t0"), ("t0", "t1"), ("t1", "snk")],
    nodes={
        "src": (from_list, {"items": ["hello", "world"]}),
        "t0": (str.upper, {}),
        "t1": (add_suffix, {"suffix": "!!"}),
        "snk": (to_list,   {"target": results}),
    },
)
# -----------------------------------------------------------

g.compile_and_run()

if __name__ == "__main__":
    assert results == ["HELLO!!", "WORLD!!"]
