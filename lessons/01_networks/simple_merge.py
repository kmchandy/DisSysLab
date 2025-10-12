# lessons.01_networks.simple_merge

from dsl import network
import time


def from_list_0():
    for item in ["A", "B"]:
        yield item
        time.sleep(0.06)


def from_list_1():
    for item in ["X", "Y", "Z"]:
        yield item
        time.sleep(0.05)


results = []
def to_results(v): results.append(v)


g = network([(from_list_0, to_results), (from_list_1, to_results)])
g.run_network()

print(results)
assert set(results) == {"A", "B", "X", "Y", "Z"}
