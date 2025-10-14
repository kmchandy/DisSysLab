# modules.ch01_networks.simple_broadcast

from dsl import network


def from_list():
    for item in ["hello", "world"]:
        yield item


results_0 = []
results_1 = []


def sink_0(item):
    results_0.append(item)


def sink_1(item):
    results_1.append(item)


# Define the network as a list of directed edges of a graph
g = network([(from_list, sink_0), (from_list, sink_1)])
g.run_network()

print(results_0)    # Output: ['hello', 'world']
print(results_1)    # Output: ['hello', 'world']
