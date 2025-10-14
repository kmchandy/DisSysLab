# lessons.03_fanout.broadcast.py

from dsl.kit import Network, FromList, Broadcast, ToList


def broadcast_example():
    results_0 = []  # Holds results sent to sink_0
    results_1 = []  # Holds results sent to sink_1
    results_2 = []  # Holds results sent to sink_2

    net = Network(
        blocks={
            "source": FromList(['a', 'b', 'c', 'd']),
            "broadcast": Broadcast(outports=["out_0", "out_1", "out_2"]),
            "sink_0": ToList(results_0),
            "sink_1": ToList(results_1),
            "sink_2": ToList(results_2),
        },
        connections=[
            ("source", "out", "broadcast", "in"),
            ("broadcast", "out_0", "sink_0", "in"),
            ("broadcast", "out_1", "sink_1", "in"),
            ("broadcast", "out_2", "sink_2", "in"),
        ],
    )

    net.compile_and_run()
    assert results_0 == ['a', 'b', 'c', 'd']
    assert results_1 == ['a', 'b', 'c', 'd']
    assert results_2 == ['a', 'b', 'c', 'd']


if __name__ == "__main__":
    broadcast_example()
