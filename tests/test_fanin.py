# tests/test_routers_fanin.py
# Simple, self-contained tests for MergeSynch and MergeAsynch
# These tests monkeypatch `recv`, `wait_for_any_port`, and `send`
# so we don't need a full Network runner.

from __future__ import annotations
from typing import Any, Dict, Iterator, Tuple

from dsl.core import Network
from dsl.block_lib.routers.fanin import MergeSynch, MergeAsynch
from dsl.block_lib.sinks.sink import Sink
from dsl.block_lib.sinks.sink_lib.common_sinks import record_to_list, record_to_set
from dsl.block_lib.sources.source import Source
from dsl.block_lib.sources.source_lib.common_sources import gen_list, gen_list_with_delay

# ---------------------------
# MergeSynch tests
# ---------------------------


def test_merge_synch_basic_with_transformer():
    """
    Two inports: 'a' and 'b'.
    Each round, MergeSynch reads one message from each inport (in order),
    applies transformer_fn(list_of_msgs), and emits the result.
    Stops when any inport yields '__STOP__'.
    """

    results = []
    network = Network(
        blocks={
            "source_a": Source(generator_fn=gen_list(["A1", "A2", "__STOP__"])),
            "source_b": Source(generator_fn=gen_list(["B1", "B2"])),
            "merge_synch": MergeSynch(inports=["a", "b"],
                                      transformer_fn=lambda xs: "/".join(xs)),
            "sink": Sink(record_fn=record_to_list(results))
        },
        connections=[
            ("source_a", "out", "merge_synch", "a"),
            ("source_b", "out", "merge_synch", "b"),
            ("merge_synch", "out", "sink", "in")
        ]
    )
    network.compile_and_run()


# ---------------------------
# MergeAsynch tests
# ---------------------------
def test_merge_asynch():
    """

    """
    results = set()
    network = Network(
        blocks={
            "source_a": Source(generator_fn=gen_list_with_delay(["A1", "A2", "__STOP__"], delay=0.15)),
            "source_b": Source(generator_fn=gen_list_with_delay(["B1", "B2"], delay=0.09)),
            "merge_asynch": MergeAsynch(inports=["a", "b"],
                                        transformer_fn=None),
            "sink": Sink(record_fn=record_to_set(results))
        },
        connections=[
            ("source_a", "out", "merge_asynch", "a"),
            ("source_b", "out", "merge_asynch", "b"),
            ("merge_asynch", "out", "sink", "in")
        ]
    )
    network.compile_and_run()
    assert results == {"A1", "A2", "B1", "B2"}


# ---------------------------
# MergeAsynch tests
# ---------------------------
def test_merge_asynch_v2():
    """

    """
    def g(msg, port):
        if port == "a":
            return msg*2
        else:
            return msg + "!!"

    results = []
    network = Network(
        blocks={
            "source_a": Source(generator_fn=gen_list_with_delay(["x1", "x2", "__STOP__"], delay=0.15)),
            "source_b": Source(generator_fn=gen_list_with_delay(["y1", "y2"], delay=0.09)),
            "merge_asynch": MergeAsynch(inports=["a", "b"],
                                        transformer_fn=g),
            "sink": Sink(record_fn=record_to_list(results))
        },
        connections=[
            ("source_a", "out", "merge_asynch", "a"),
            ("source_b", "out", "merge_asynch", "b"),
            ("merge_asynch", "out", "sink", "in")
        ]
    )
    network.compile_and_run()
    assert results == ['x1x1', 'y1!!', 'y2!!', 'x2x2']


# ---------------------------
# Plain-Python runner
# ---------------------------


if __name__ == "__main__":
    test_merge_synch_basic_with_transformer()
    test_merge_asynch()
    test_merge_asynch_v2()
    print("All tests passed.")
