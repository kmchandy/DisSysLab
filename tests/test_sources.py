# tests/test_sources.py
from dsl.core import Network
from dsl.block_lib.sources.source import Source
from dsl.block_lib.sources.source_lib.common_classes import FromRandomIntegers
from dsl.block_lib.sinks.sink_lib.common_classes import ToList


def _run_network(blocks, connections):
    """Helper: build, compile, run synchronously."""
    net = Network(blocks=blocks, connections=connections)
    net.compile_and_run()
    return net


def test_source_emits_items_and_stop():
    results = []

    def gen():
        yield 1
        yield 2

    src = Source(generator_fn=gen)
    sink = ToList(results)

    _run_network(
        {"src": src, "sink": sink},
        [("src", "out", "sink", "in")]
    )

    assert results == [1, 2]


def test_source_empty_generator_sends_stop_only():
    results = []

    def gen():
        yield from []

    src = Source(generator_fn=gen)
    sink = ToList(results)

    _run_network(
        {"src": src, "sink": sink},
        [("src", "out", "sink", "in")]
    )

    assert results == []  # no messages before STOP


def test_source_generator_raises_after_first_item():
    results = []

    def gen():
        yield "ok"
        raise RuntimeError("boom")

    src = Source(generator_fn=gen)
    sink = ToList(results)

    _run_network(
        {"src": src, "sink": sink},
        [("src", "out", "sink", "in")]
    )

    # First item should be delivered; then STOP after error.
    assert results == ["ok"]


def test_source_generator_random():

    src = FromRandomIntegers(N=5, LOW=1, HIGH=10)

    results = []
    sink = ToList(results)

    _run_network(
        {"src": src, "sink": sink},
        [("src", "out", "sink", "in")]
    )
    print(f"results = {results}")
    assert len(results) == 5
    assert all(1 <= x <= 10 for x in results)


if __name__ == "__main__":
    test_source_emits_items_and_stop()
    test_source_empty_generator_sends_stop_only()
    test_source_generator_raises_after_first_item()
    test_source_generator_random()
