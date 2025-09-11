from dsl.kit import FromList, ToList, Uppercase, Network, pipeline


def basic_network():
    results = []  # Holds results sent to sink

    net = Network(
        blocks={
            "source": FromList(['hello', 'world']),
            "transform": Uppercase(),
            "sink": ToList(results),
        },
        connections=[
            ("source", "out", "transform", "in"),
            ("transform", "out", "sink", "in"),
        ],
    )

    net.compile_and_run()
    assert results == ['HELLO', 'WORLD']


def simple_pipeline():
    results = []  # Holds results sent to sink

    net = pipeline([FromList(['hello', 'world']),
                   Uppercase(), ToList(results)])

    net.compile_and_run()
    assert results == ['HELLO', 'WORLD']


if __name__ == "__main__":
    basic_network()
    simple_pipeline()
    print("All examples ran successfully.")
