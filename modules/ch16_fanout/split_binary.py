# lessons.03_fanout.spit_binary.py
from dsl.kit import Network, FromList, ToList, SplitBinary


def split_binary():
    """
    Outport "out_0" receives values for which func returns False.
    Outport "out_1" receives values for which func returns True.
    Stops when any inport yields '__STOP__'.
    """
    def f(x):
        return x % 2

    results_0 = []
    results_1 = []
    network = Network(
        blocks={
            "source": FromList([0, 1, 2, 3, 4]),
            "split_binary": SplitBinary(func=f),
            "sink_0": ToList(results_0),
            "sink_1": ToList(results_1)
        },
        connections=[
            ("source", "out", "split_binary", "in"),
            ("split_binary", "out_0", "sink_0", "in"),
            ("split_binary", "out_1", "sink_1", "in")
        ]
    )
    network.compile_and_run()
    assert results_0 == [0, 2, 4]
    assert results_1 == [1, 3]


if __name__ == "__main__":
    split_binary()
