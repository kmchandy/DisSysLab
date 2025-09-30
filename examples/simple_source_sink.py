from dsl import network
import time

# Define functions.


def from_list():
    for item in ["hello", "world"]:
        yield item
        time.sleep(0.1)


results = []


def to_results(v):
    results.append(v)


# Define the network
g = network([(from_list, to_results)])
g.run_network()

if __name__ == "__main__":
    assert (results == ["hello", "world"])
