# tests/test_termination.py
"""
Tests for os_agent termination detection.

Two tests:
1. Single source → single sink: simplest possible network.
2. Source → transform → sink: standard three-node pipeline.

Both tests verify that the network terminates correctly without timeout,
and that all messages are delivered (counts match).
"""

import pytest
from dsl import network
from dsl.blocks import Source, Transform, Sink


# ── Test 1: source → sink ─────────────────────────────────────────────────────

def test_single_source_to_sink():
    """
    Simplest possible network: one source, one sink.
    Source emits 5 messages then exhausts.
    os_agent should detect termination and shut down sink cleanly.
    """
    messages = [{"value": i} for i in range(5)]
    index = [0]

    def source_fn():
        if index[0] >= len(messages):
            return None
        msg = messages[index[0]]
        index[0] += 1
        return msg

    received = []

    def sink_fn(msg):
        received.append(msg)

    src = Source(fn=source_fn, name="src")
    sink = Sink(fn=sink_fn, name="sink")

    g = network([(src, sink)])
    g.run_network(timeout=10)

    assert len(received) == 5
    assert [m["value"] for m in received] == list(range(5))


# ── Test 2: source → transform → sink ────────────────────────────────────────

def test_source_transform_sink():
    """
    Three-node pipeline: source → transform → sink.
    Source emits 5 messages. Transform doubles the value.
    os_agent should detect termination and shut down all agents cleanly.
    """
    messages = [{"value": i} for i in range(5)]
    index = [0]

    def source_fn():
        if index[0] >= len(messages):
            return None
        msg = messages[index[0]]
        index[0] += 1
        return msg

    def double(msg):
        return {"value": msg["value"] * 2}

    received = []

    def sink_fn(msg):
        received.append(msg)

    src = Source(fn=source_fn, name="src")
    transform = Transform(fn=double, name="double")
    sink = Sink(fn=sink_fn, name="sink")

    g = network([
        (src,       transform),
        (transform, sink),
    ])
    g.run_network(timeout=10)

    assert len(received) == 5
    assert [m["value"] for m in received] == [0, 2, 4, 6, 8]


if __name__ == "__main__":
    print("Test 1: source → sink")
    test_single_source_to_sink()
    print("  ✓ passed")

    print("Test 2: source → transform → sink")
    test_source_transform_sink()
    print("  ✓ passed")

    print()
    print("All termination tests passed.")
