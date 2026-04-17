# tests/unit/test_blocks.py
"""
Tests for all block types.

Tests use full network() + run_network() rather than manual queue manipulation.
Termination is handled by os_agent — no STOP signals needed.
"""

import pytest
from dissyslab import network
from dissyslab.blocks import Source, Transform, Sink, Broadcast, MergeAsynch, Split


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_source(items):
    """Return a Source that emits items then exhausts."""
    data = list(items)
    index = [0]

    def fn():
        if index[0] >= len(data):
            return None
        val = data[index[0]]
        index[0] += 1
        return val

    return Source(fn=fn)


def collect_sink():
    """Return (sink, results_list) pair."""
    results = []
    sink = Sink(fn=results.append)
    return sink, results


# ── Source ────────────────────────────────────────────────────────────────────

class TestSource:

    def test_source_requires_callable(self):
        with pytest.raises(TypeError, match="must be callable"):
            Source(fn="not callable")

    def test_source_generates_messages(self):
        sink, results = collect_sink()
        g = network([(make_source([1, 2, 3]), sink)])
        g.run_network(timeout=5)
        assert results == [1, 2, 3]

    def test_source_exhausts_cleanly(self):
        """Source with zero messages terminates immediately."""
        sink, results = collect_sink()
        g = network([(make_source([]), sink)])
        g.run_network(timeout=5)
        assert results == []

    def test_source_has_default_outport(self):
        src = Source(fn=lambda: None)
        assert src.default_outport == "out_"

    def test_source_generator_function(self):
        """Source wraps generator functions automatically."""
        def gen():
            yield 1
            yield 2
            yield 3

        sink, results = collect_sink()
        g = network([(Source(fn=gen), sink)])
        g.run_network(timeout=5)
        assert results == [1, 2, 3]


# ── Transform ─────────────────────────────────────────────────────────────────

class TestTransform:

    def test_transform_requires_callable(self):
        with pytest.raises(TypeError, match="must be callable"):
            Transform(fn="not callable")

    def test_transform_applies_function(self):
        sink, results = collect_sink()
        transform = Transform(fn=lambda x: x * 2)
        g = network([
            (make_source([5, 10]), transform),
            (transform, sink),
        ])
        g.run_network(timeout=5)
        assert results == [10, 20]

    def test_transform_filters_none(self):
        def filter_positive(x):
            return x if x > 0 else None

        src = make_source([-5, 10, -3, 7])
        transform = Transform(fn=filter_positive)
        sink, results = collect_sink()
        g = network([(src, transform), (transform, sink)])
        g.run_network(timeout=5)
        assert results == [10, 7]

    def test_transform_with_params(self):
        def scale(x, factor):
            return x * factor

        src = make_source([5, 10])
        transform = Transform(fn=scale, params={"factor": 10})
        sink, results = collect_sink()
        g = network([(src, transform), (transform, sink)])
        g.run_network(timeout=5)
        assert results == [50, 100]

    def test_transform_has_default_ports(self):
        transform = Transform(fn=lambda x: x)
        assert transform.default_inport == "in_"
        assert transform.default_outport == "out_"


# ── Sink ──────────────────────────────────────────────────────────────────────

class TestSink:

    def test_sink_requires_callable(self):
        with pytest.raises(TypeError, match="must be callable"):
            Sink(fn="not callable")

    def test_sink_calls_function(self):
        sink, results = collect_sink()
        g = network([(make_source([1, 2, 3]), sink)])
        g.run_network(timeout=5)
        assert results == [1, 2, 3]

    def test_sink_with_params(self):
        results = []

        def collect_with_prefix(msg, prefix):
            results.append(f"{prefix}{msg}")

        src = make_source(["hello", "world"])
        sink = Sink(fn=collect_with_prefix, params={"prefix": ">> "})
        g = network([(src, sink)])
        g.run_network(timeout=5)
        assert results == [">> hello", ">> world"]

    def test_sink_has_default_inport(self):
        sink = Sink(fn=print)
        assert sink.default_inport == "in_"


# ── Broadcast ─────────────────────────────────────────────────────────────────

class TestBroadcast:

    def test_broadcast_requires_positive_outputs(self):
        with pytest.raises(ValueError, match="at least 1 output"):
            Broadcast(num_outputs=0)

    def test_broadcast_copies_to_all(self):
        """Broadcast sends to all outputs — auto-inserted by network."""
        src = make_source([1, 2, 3])
        sink_a, results_a = collect_sink()
        sink_b, results_b = collect_sink()

        # network auto-inserts Broadcast for fanout
        g = network([
            (src, sink_a),
            (src, sink_b),
        ])
        g.run_network(timeout=5)

        assert sorted(results_a) == [1, 2, 3]
        assert sorted(results_b) == [1, 2, 3]

    def test_broadcast_deep_copies(self):
        """Broadcast creates independent copies — mutations don't cross."""
        mutated = []
        original = []

        def mutate(msg):
            msg["mutated"] = True
            mutated.append(msg)

        def record(msg):
            original.append(dict(msg))

        src = make_source([{"value": 1}])
        sink_mutate = Sink(fn=mutate)
        sink_record = Sink(fn=record)

        g = network([
            (src, sink_mutate),
            (src, sink_record),
        ])
        g.run_network(timeout=5)

        # record sink should not see mutation
        assert original[0].get("mutated") is None

    def test_broadcast_has_default_inport(self):
        broadcast = Broadcast(num_outputs=2)
        assert broadcast.default_inport == "in_"

    def test_broadcast_no_default_outport(self):
        broadcast = Broadcast(num_outputs=2)
        assert broadcast.default_outport is None


# ── MergeAsynch ───────────────────────────────────────────────────────────────

class TestMergeAsynch:

    def test_merge_requires_positive_inputs(self):
        with pytest.raises(ValueError, match="at least 1 input"):
            MergeAsynch(num_inputs=0)

    def test_merge_combines_inputs(self):
        """MergeAsynch combines multiple inputs — auto-inserted by network."""
        src_a = make_source([1, 2])
        src_b = make_source([10, 20])
        sink, results = collect_sink()

        # network auto-inserts MergeAsynch for fanin
        g = network([
            (src_a, sink),
            (src_b, sink),
        ])
        g.run_network(timeout=5)

        assert sorted(results) == [1, 2, 10, 20]

    def test_merge_no_default_inport(self):
        merge = MergeAsynch(num_inputs=2)
        assert merge.default_inport is None

    def test_merge_has_default_outport(self):
        merge = MergeAsynch(num_inputs=2)
        assert merge.default_outport == "out_"


# ── Split ─────────────────────────────────────────────────────────────────────

class TestSplit:

    def test_split_requires_callable(self):
        with pytest.raises(TypeError, match="must be callable"):
            Split(fn="not callable", num_outputs=2)

    def test_split_requires_multiple_outputs(self):
        with pytest.raises(ValueError, match="at least 2 outputs"):
            Split(fn=lambda x: [x], num_outputs=1)

    def test_split_routes_messages(self):
        def even_odd(x):
            if x % 2 == 0:
                return [x, None]
            else:
                return [None, x]

        src = make_source([2, 3, 4])
        split = Split(fn=even_odd, num_outputs=2)
        sink_even, results_even = collect_sink()
        sink_odd, results_odd = collect_sink()

        g = network([
            (src,           split),
            (split.out_0,   sink_even),
            (split.out_1,   sink_odd),
        ])
        g.run_network(timeout=5)

        assert results_even == [2, 4]
        assert results_odd == [3]

    def test_split_multicast(self):
        def multicast(x):
            if x > 10:
                return [x, x]
            else:
                return [x, None]

        src = make_source([5, 15])
        split = Split(fn=multicast, num_outputs=2)
        sink_a, results_a = collect_sink()
        sink_b, results_b = collect_sink()

        g = network([
            (src,           split),
            (split.out_0,   sink_a),
            (split.out_1,   sink_b),
        ])
        g.run_network(timeout=5)

        assert results_a == [5, 15]
        assert results_b == [15]

    def test_split_has_default_inport(self):
        split = Split(fn=lambda x: [x, None], num_outputs=2)
        assert split.default_inport == "in_"

    def test_split_no_default_outport(self):
        split = Split(fn=lambda x: [x, None], num_outputs=2)
        assert split.default_outport is None
