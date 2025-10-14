# modules.ch01_networks.basic_network.py

from dsl import network


def from_list():
    for item in ["hello", "world"]:
        yield item


def uppercase(item):
    return item.upper()


results = []


def to_results(item):
    results.append(item)


# Define the network as a list of directed edges of a graph
g = network([(from_list, uppercase), (uppercase, to_results)])

g.run_network()
print(results)  # Output: ['HELLO', 'WORLD']
