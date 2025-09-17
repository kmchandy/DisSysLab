# lessons.01_networks_blocks_connections.basic_network.py

from dsl.kit import Network, FromList, Uppercase, ToList


def basic_network():
    results = []  # Holds results sent to sink

    net = Network(
        blocks={
            "source": FromList(['hello', 'world', "__STOP__"]),
            "upper_case": Uppercase(),
            "sink": ToList(results),
        },
        connections=[
            ("source", "out", "upper_case", "in"),
            ("upper_case", "out", "sink", "in"),
        ],
    )

    net.compile_and_run()
    print("Results:", results)
    assert results == ['HELLO', 'WORLD']


if __name__ == "__main__":
    basic_network()
