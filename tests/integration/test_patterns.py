"""Integration tests for fanout and fanin patterns."""

import pytest
from dsl import network
from dsl.blocks import Source, Sink, Split


class TestFanoutPattern:
    """Test fanout (one → many) patterns."""

    def test_fanout_to_multiple_sinks(self):
        """One source fans out to multiple sinks."""
        results_a = []
        results_b = []
        results_c = []

        class ListSource:
            def __init__(self):
                self.data = [1, 2, 3]
                self.index = 0

            def run(self):
                if self.index >= len(self.data):
                    return None
                val = self.data[self.index]
                self.index += 1
                return val

        data = ListSource()
        source = Source(fn=data.run, name="src")
        sink_a = Sink(fn=results_a.append, name="sink_a")
        sink_b = Sink(fn=results_b.append, name="sink_b")
        sink_c = Sink(fn=results_c.append, name="sink_c")

        g = network([
            (source, sink_a),
            (source, sink_b),
            (source, sink_c)
        ])

        g.run_network()

        # All sinks should receive all messages
        assert results_a == [1, 2, 3]
        assert results_b == [1, 2, 3]
        assert results_c == [1, 2, 3]


class TestFaninPattern:
    """Test fanin (many → one) patterns."""

    def test_fanin_from_multiple_sources(self):
        """Multiple sources fan in to one sink."""
        results = []

        class ListSource:
            def __init__(self, data):
                self.data = data
                self.index = 0

            def run(self):
                if self.index >= len(self.data):
                    return None
                val = self.data[self.index]
                self.index += 1
                return val

        data_a = ListSource([1, 2])
        data_b = ListSource([10, 20])
        data_c = ListSource([100, 200])

        src_a = Source(fn=data_a.run, name="src_a")
        src_b = Source(fn=data_b.run, name="src_b")
        src_c = Source(fn=data_c.run, name="src_c")
        sink = Sink(fn=results.append, name="sink")

        g = network([
            (src_a, sink),
            (src_b, sink),
            (src_c, sink)
        ])

        g.run_network()

        # All messages should be received (order may vary)
        assert set(results) == {1, 2, 10, 20, 100, 200}
        assert len(results) == 6


class TestSplitPattern:
    """Test split (routing) patterns."""

    def test_split_even_odd(self):
        """Split routes even/odd numbers to different outputs."""
        evens = []
        odds = []

        class ListSource:
            def __init__(self):
                self.data = [1, 2, 3, 4, 5, 6]
                self.index = 0

            def run(self):
                if self.index >= len(self.data):
                    return None
                val = self.data[self.index]
                self.index += 1
                return val

        def even_odd_router(x):
            if x % 2 == 0:
                return [x, None]  # Even → out_0
            else:
                return [None, x]  # Odd → out_1

        data = ListSource()
        source = Source(fn=data.run, name="src")
        split = Split(fn=even_odd_router, num_outputs=2, name="split")
        even_sink = Sink(fn=evens.append, name="evens")
        odd_sink = Sink(fn=odds.append, name="odds")

        g = network([
            (source, split),
            (split.out_0, even_sink),
            (split.out_1, odd_sink)
        ])

        g.run_network()

        assert evens == [2, 4, 6]
        assert odds == [1, 3, 5]

    def test_split_multicast(self):
        """Split can send to multiple outputs (multicast)."""
        low = []
        high = []

        class ListSource:
            def __init__(self):
                self.data = [5, 15, 25]
                self.index = 0

            def run(self):
                if self.index >= len(self.data):
                    return None
                val = self.data[self.index]
                self.index += 1
                return val

        def multicast_router(x):
            if x > 20:
                return [x, x]  # Send to both outputs
            elif x > 10:
                return [None, x]  # Send to high only
            else:
                return [x, None]  # Send to low only

        data = ListSource()
        source = Source(fn=data.run, name="src")
        split = Split(fn=multicast_router, num_outputs=2, name="split")
        low_sink = Sink(fn=low.append, name="low")
        high_sink = Sink(fn=high.append, name="high")

        g = network([
            (source, split),
            (split.out_0, low_sink),
            (split.out_1, high_sink)
        ])

        g.run_network()

        assert low == [5, 25]  # 5 (low only), 25 (both)
        assert high == [15, 25]  # 15 (high only), 25 (both)
