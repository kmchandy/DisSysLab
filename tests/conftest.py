"""Shared test fixtures and utilities."""

import pytest
from queue import SimpleQueue
from dsl.blocks import Source, Transform, Sink, Split, Broadcast, MergeAsynch


@pytest.fixture
def simple_source():
    """Create a simple list-based source."""
    class ListSource:
        def __init__(self, items):
            self.items = items
            self.index = 0

        def run(self):
            if self.index >= len(self.items):
                return None
            item = self.items[self.index]
            self.index += 1
            return item

    return lambda items: Source(fn=ListSource(items).run, name="src")


@pytest.fixture
def collector():
    """Create a collector sink that appends to a list."""
    results = []
    sink = Sink(fn=results.append, name="collector")
    return sink, results


@pytest.fixture
def simple_queue():
    """Create a SimpleQueue for testing."""
    return SimpleQueue()
