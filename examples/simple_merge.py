# dsl.examples.simple_merge

from dsl import Graph
import time

# -----------------------------------------------------------
# Define Python functions independent of dsl.
# -----------------------------------------------------------


def from_list(items, delay):
    for item in items:
        yield item
        time.sleep(delay)


def src_0():
    return from_list(items=["A", "B"], delay=0.5)


def src_1():
    return from_list(items=["X", "Y", "Z"], delay=0.4)


def trn_0(v): return v.lower()
def trn_1(v): return v + "!!"
def snk(v): results.append(v)


# -----------------------------------------------------------
# Define the graph
# -----------------------------------------------------------
results = []

g = Graph(
    edges=[("src_0", "trn_0"), ("src_1", "trn_0"),
           ('src_0', "trn_1"), ("src_1", "trn_1"),
           ("trn_0", "snk"), ("trn_1", "snk")],
    nodes=[("src_0", src_0), ("src_1", src_1), ("trn_0", trn_0),
           ("trn_1", trn_1), ("snk", snk)]
)
# -----------------------------------------------------------

g.compile_and_run()
if __name__ == "__main__":
    assert set(results) == {"A!!", "B!!", "X!!", "Y!!", "Z!!",
                            "a", "b", "x", "y", "z"}
