"""Integration tests for complete pipelines."""

import pytest
from dsl import network
from dsl.blocks import Source, Transform, Sink


class TestSimplePipelines:
    """Test complete pipeline execution."""

    def test_source_sink_pipeline(self):
        """Source → Sink pipeline."""
        results = []

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
        sink = Sink(fn=results.append, name="sink")

        g = network([
            (source, sink)
        ])

        g.run_network()

        assert results == [1, 2, 3]

    def test_source_transform_sink_pipeline(self):
        """Source → Transform → Sink pipeline."""
        results = []

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
        transform = Transform(fn=lambda x: x * 2, name="double")
        sink = Sink(fn=results.append, name="sink")

        g = network([
            (source, transform),
            (transform, sink)
        ])

        g.run_network()

        assert results == [2, 4, 6]

    def test_transform_with_filter(self):
        """Transform filters None results."""
        results = []

        class ListSource:
            def __init__(self):
                self.data = [1, -2, 3, -4, 5]
                self.index = 0

            def run(self):
                if self.index >= len(self.data):
                    return None
                val = self.data[self.index]
                self.index += 1
                return val

        def filter_positive(x):
            return x if x > 0 else None

        data = ListSource()
        source = Source(fn=data.run, name="src")
        transform = Transform(fn=filter_positive, name="filter")
        sink = Sink(fn=results.append, name="sink")

        g = network([
            (source, transform),
            (transform, sink)
        ])

        g.run_network()

        assert results == [1, 3, 5]

    def test_multiple_transforms(self):
        """Chain multiple transforms."""
        results = []

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
        double = Transform(fn=lambda x: x * 2, name="double")
        add_ten = Transform(fn=lambda x: x + 10, name="add_ten")
        sink = Sink(fn=results.append, name="sink")

        g = network([
            (source, double),
            (double, add_ten),
            (add_ten, sink)
        ])

        g.run_network()

        assert results == [12, 14, 16]  # (1*2)+10, (2*2)+10, (3*2)+10
