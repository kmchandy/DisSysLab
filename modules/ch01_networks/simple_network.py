# modules.ch01_networks.simple_network.py

from dsl import network
import time

# Define functions.


def from_list_0():
    for item in ["A", "B"]:
        yield item
        time.sleep(0.12)


def from_list_1():
    for item in ["X", "Y", "Z"]:
        yield item
        time.sleep(0.1)


def lower(v):
    return v.lower()


def add_bangs(v):
    return v + "!!"


results = []
def to_results(v): results.append(v)


# Define the graph
g = network([(from_list_0, lower), (from_list_1, lower),
            (from_list_0, add_bangs), (from_list_1, add_bangs),
            (lower, to_results), (add_bangs, to_results)])
g.run_network()

if __name__ == "__main__":
    print(set(results))
    assert set(results) == {"A!!", "B!!", "X!!", "Y!!", "Z!!",
                            "a", "b", "x", "y", "z"}
