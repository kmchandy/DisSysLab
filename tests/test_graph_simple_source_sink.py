from dsl import Graph, from_list, to_list


def test_simple():
    out = []
    g = Graph(edges=[("src", "snk")],
              nodes={"src": (from_list, {"items": [1, 2, 3]}),
                     "snk": (to_list, {"target": out})})
    g.compile_and_run()

    assert out == [1, 2, 3]
