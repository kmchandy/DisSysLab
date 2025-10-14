# modules.ch01_networks.simple_filter

from dsl import network

# Define functions.

list_of_words = ['t', 'hello', 'world', 'python', 'philosophy', 'is', 'fun']


def from_list(items=list_of_words):
    for item in items:
        yield item


def drop(v, min_length=2, max_length=8):
    if min_length <= len(v) <= max_length:
        return v
    else:
        return None


results = []
def to_results(v): results.append(v)


# Define the network.
g = network([(from_list, drop), (drop, to_results)])
g.run_network()

print(results)
assert results == ['hello', 'world', 'python', 'is', 'fun']
