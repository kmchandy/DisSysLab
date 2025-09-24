from dsl import Graph, from_list, to_list

results = []
g = Graph(
    edges=[("src", "snk")],
    nodes={
        "src": (from_list, {"items": ["hello", None, "world"]}),
        "snk": (to_list,   {"target": results}),
    },
)
g.compile_and_run()
print(results)
