# dsl.examples.graph_pipeline

from dsl import Graph

# -----------------------------------------------------------
# Define Python functions independent of dsl.
# -----------------------------------------------------------


def src():
    for item in ["hello", "world"]:
        yield item


results_0 = []
def snk_0(v): results_0.append(v)


results_1 = []
def snk_1(v): results_1.append(v)


# -----------------------------------------------------------
# Define the graph
# -----------------------------------------------------------
results_0 = []
results_1 = []
g = Graph(
    edges=[("src", "snk_0"), ("src", "snk_1")],
    nodes=[("src", src), ("snk_0", snk_0), ("snk_1", snk_1)]
)
# -----------------------------------------------------------

g.compile_and_run()

if __name__ == "__main__":
    assert results_0 == ['hello', 'world']
    assert results_1 == ['hello', 'world']
