# dsl.examples.graph_pipeline

from dsl import Graph

# -----------------------------------------------------------
# Define Python functions.
# -----------------------------------------------------------


def src():
    for item in ["hello", "world"]:
        yield item


def t_0(v): return v.upper()
def t_1(v): return v + "!!"


results = []
def snk(v): results.append(v)


# -----------------------------------------------------------
# Define the graph
# -----------------------------------------------------------

g = Graph(
    edges=[("src", "t_0"), ("t_0", "t_1"), ("t_1", "snk")],
    nodes=[("src", src), ("t_0", t_0), ("t_1", t_1), ("snk", snk)]
)
# -----------------------------------------------------------

g.compile_and_run()

if __name__ == "__main__":
    assert results == ["HELLO!!", "WORLD!!"]
