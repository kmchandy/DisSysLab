# dsl.examples.simple_pipeline

from dsl import network

# Define Python functions.


def src():
    for item in ["hello", "world"]:
        yield item


def t_0(v): return v.upper()
def t_1(v): return v + "!!"


results = []
def snk(v): results.append(v)


# Define and run the graph
g = network([(src, t_0), (t_0, t_1), (t_1, snk)])
g.run_network()

if __name__ == "__main__":
    assert results == ["HELLO!!", "WORLD!!"]
