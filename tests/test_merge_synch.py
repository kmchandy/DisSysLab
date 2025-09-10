# tests/test_routers_fanin.py
# Simple, self-contained tests for MergeSynch and MergeAsynch
# These tests monkeypatch `recv`, `wait_for_any_port`, and `send`
# so we don't need a full Network runner.

from __future__ import annotations
from typing import Any, Dict, Iterator, Tuple

from dsl.core import Network
from dsl.block_lib.routers.fanin import MergeSynch, MergeAsynch
from dsl.block_lib.sinks.sink import Sink
from dsl.block_lib.sinks.sink_lib.common_sinks import record_to_list
from dsl.block_lib.sources.source import Source
from dsl.block_lib.sources.source_lib.common_sources import gen_list

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
    out = []

    ms = MergeSynch(
        inports=["a", "b"],
        transformer_fn=lambda xs: "/".join(xs),  # map ['A1','B1'] -> 'A1/B1'
        name="MS1",
    )

    results = []
    network = Network(
        blocks={
            "source_a": Source(generator_fn=gen_list(["A1", "A2", "__STOP__"])),
            "source_b": Source(generator_fn=gen_list(["B1", "B2"])),
            "merge_synch": MergeSynch(inports=["a", "b"],
                                      transformer_fn=lambda xs: "/".join(xs)),
            "sink": Sink(record_fn=record_to_list(target_list=results))
        },
        connections=[
            ("source_a", "out", "merge_synch", "a"),
            ("source_b", "out", "merge_synch", "b"),
            ("merge_synch", "out", "sink", "in")
        ]
    )
    network.compile_and_run()
    print(f"Results: {results}")
    assert results == ["A1/B1", "A2/B2", "__STOP__"]


def test_merge_synch_no_transformer_passthrough_list():
    """
    Without a transformer_fn, MergeSynch should emit the list of inputs.
    """
    out = []

    ms = MergeSynch(inports=["x", "y"], transformer_fn=None, name="MS2")

    iters = _iter({
        "x": [1, 2, "__STOP__"],
        "y": [10, 20],
    })

    ms.recv = lambda port: next(iters[port])  # type: ignore[method-assign]
    ms.send = lambda msg, port="out": out.append(
        msg)  # type: ignore[method-assign]

    ms.run()

    assert out == [[1, 10], [2, 20], "__STOP__"]


# ---------------------------
# MergeAsynch tests
# ---------------------------

def test_merge_asynch_basic_with_transformer():
    """
    MergeAsynch emits as messages arrive from ANY inport.
    It should only emit a single '__STOP__' after ALL inports have sent STOP.
    """
    out = []

    ma = MergeAsynch(
        inports=["a", "b"],
        transformer_fn=lambda msg, port: f"{port}:{msg}",
        name="MA1",
    )

    # Sequence of (msg, port) arrivals (interleaved), then STOP from each port.
    arrivals: Iterator[Tuple[Any, str]] = iter([
        ("a1", "a"),
        ("b1", "b"),
        ("a2", "a"),
        ("__STOP__", "a"),
        ("b2", "b"),
        ("__STOP__", "b"),  # after this, all ports have STOPped -> emit STOP and return
    ])

    ma.wait_for_any_port = lambda: next(
        arrivals)  # type: ignore[method-assign]
    ma.send = lambda msg, port="out": out.append(
        msg)  # type: ignore[method-assign]

    ma.run()

    assert out == ["a:a1", "b:b1", "a:a2", "b:b2", "__STOP__"]


def test_merge_asynch_no_transformer_passthrough():
    """
    Without a transformer_fn, MergeAsynch should pass through raw messages.
    """
    out = []

    ma = MergeAsynch(inports=["x", "y"], transformer_fn=None, name="MA2")

    arrivals: Iterator[Tuple[Any, str]] = iter([
        (100, "x"),
        ("hello", "y"),
        (200, "x"),
        ("__STOP__", "x"),
        ("__STOP__", "y"),
    ])

    ma.wait_for_any_port = lambda: next(
        arrivals)  # type: ignore[method-assign]
    ma.send = lambda msg, port="out": out.append(
        msg)  # type: ignore[method-assign]

    ma.run()

    assert out == [100, "hello", 200, "__STOP__"]


# ---------------------------
# Plain-Python runner
# ---------------------------

def main():
    for fn in [
        test_merge_synch_basic_with_transformer,
        test_merge_synch_no_transformer_passthrough_list,
        test_merge_asynch_basic_with_transformer,
        test_merge_asynch_no_transformer_passthrough,
    ]:
        fn()
        print(f"{fn.__name__}: PASS")


if __name__ == "__main__":
    test_merge_synch_basic_with_transformer()
