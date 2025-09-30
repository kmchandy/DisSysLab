# dsl.examples.graph_pipeline

from dsl import network

# Define Python functions.


def from_list():
    for item in ["hello", "world"]:
        yield item


results_0 = []
def snk_0(v): results_0.append(v)


results_1 = []
def snk_1(v): results_1.append(v)


# Define the graph
g = network([(from_list, snk_0), (from_list, snk_1)])
g.run_network()

if __name__ == "__main__":
    assert results_0 == ['hello', 'world']
    assert results_1 == ['hello', 'world']
