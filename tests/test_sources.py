# tests/test_sources.py

import time
import threading
import pytest

from dsl.core import Agent, Network, STOP
from dsl.block_lib.sources.source import Source


class _ListSink(Agent):
    """Minimal sink for tests: collects messages until STOP."""

    def __init__(self, out_list, name="ListSink"):
        super().__init__(name=name, inports=["in"], outports=[], run=self.run)
        self._out = out_list

    def run(self):
        while True:
            msg = self.recv("in")
            if msg == STOP:
                return
            self._out.append(msg)


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
    sink = _ListSink(results)

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
    sink = _ListSink(results)

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
    sink = _ListSink(results)

    _run_network(
        {"src": src, "sink": sink},
        [("src", "out", "sink", "in")]
    )

    # First item should be delivered; then STOP after error.
    assert results == ["ok"]


def test_source_generator_random():
    import random

    def my_generator(N, LOW, HIGH):
        i = 0
        while i < N:
            yield random.randint(LOW, HIGH)
            i += 1

    src = Source(name="Rand_N", generator_fn=my_generator, N=5, LOW=1, HIGH=10)

    results = []
    sink = _ListSink(results)

    _run_network(
        {"src": src, "sink": sink},
        [("src", "out", "sink", "in")]
    )
    assert len(results) == 5
    assert all(1 <= x <= 10 for x in results)


if __name__ == "__main__":
    test_source_emits_items_and_stop()
    test_source_empty_generator_sends_stop_only()
    test_source_generator_raises_after_first_item()
    test_source_generator_random()
