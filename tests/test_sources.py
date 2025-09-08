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


def test_source_delay_respected():
    results = []

    N = 3
    delay = 0.05  # 50 ms per item, loose check

    def gen():
        for i in range(N):
            yield i

    src = Source(generator_fn=gen, delay=delay)
    sink = _ListSink(results)

    start = time.monotonic()
    _run_network(
        {"src": src, "sink": sink},
        [("src", "out", "sink", "in")]
    )
    elapsed = time.monotonic() - start

    # Expect at least N * delay minus a small scheduling tolerance.
    # (Sleep happens after each send; for N items, ~N * delay.)
    assert elapsed >= N * delay * 0.8
    assert results == list(range(N))
