# dsl.examples.graph_pipeline

from dsl import network

# Define Python functions.


def from_list():
    for item in ["hello", "world"]:
        yield item


results_0 = []
results_1 = []


def sink_0(item):
    results_0.append(item)


def sink_1(item):
    results_1.append(item)


# Define the graph
g = network([(from_list, sink_0), (from_list, sink_1)])
g.run_network()

if __name__ == "__main__":
    assert results_0 == ['hello', 'world']
    assert results_1 == ['hello', 'world']
