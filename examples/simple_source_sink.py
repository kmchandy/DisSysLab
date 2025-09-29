from dsl import Graph


def from_list(items):
    for item in items:
        yield item


def to_list(v, target):
    target.append(v)


def src():
    return from_list(items=["hello", "world"])


def snk(v):
    return to_list(v, target=results)


results = []
g = Graph(
    edges=[("src", "snk")],
    nodes=[("src", src), ("snk", snk)]
)
g.compile_and_run()

if __name__ == "__main__":
    assert results == ["hello", "world"]
