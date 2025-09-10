from dsl.core import Network
from dsl.block_lib.sources.source import Source
from dsl.block_lib.sinks.sink import Sink
from dsl.block_lib.sinks.sink_lib.common_sinks import record_to_list
from dsl.block_lib.sources.source import Source
from dsl.block_lib.sources.source_lib.common_sources import gen_list, gen_list_with_delay
from dsl.block_lib.routers.fanout import Broadcast, TwoWaySplit


def test_broadcast():
    """
    Outports "a" and "b" both receive all values from the source.
    Stops when any inport yields '__STOP__'.
    """

    results_a = []
    results_b = []
    network = Network(
        blocks={
            "source": Source(generator_fn=gen_list(["A1", "A2", "__STOP__"])),
            "broadcast": Broadcast(outports=["a", "b"]),
            "sink_a": Sink(record_fn=record_to_list(results_a)),
            "sink_b": Sink(record_fn=record_to_list(results_b))
        },
        connections=[
            ("source", "out", "broadcast", "in"),
            ("broadcast", "a", "sink_a", "in"),
            ("broadcast", "b", "sink_b", "in")
        ]
    )
    network.compile_and_run()
    assert results_a == ["A1", "A2"]
    assert results_b == ["A1", "A2"]


def test_two_way_split():
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
            "source": Source(generator_fn=gen_list([0, 1, 2, 3, 4, "__STOP__"])),
            "two_way_split": TwoWaySplit(func=f),
            "sink_0": Sink(record_fn=record_to_list(results_0)),
            "sink_1": Sink(record_fn=record_to_list(results_1))
        },
        connections=[
            ("source", "out", "two_way_split", "in"),
            ("two_way_split", "out_0", "sink_0", "in"),
            ("two_way_split", "out_1", "sink_1", "in")
        ]
    )
    network.compile_and_run()
    assert results_0 == [0, 2, 4]
    assert results_1 == [1, 3]


if __name__ == "__main__":
    test_broadcast()
    test_two_way_split()
    print(f"All tests passed.")
