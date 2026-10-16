"""Shared test fixtures and utilities."""

import pytest
from queue import SimpleQueue
from dissyslab.blocks import Source, Transform, Sink, Split, Broadcast, MergeAsynch


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


# ── The suite must not write into the repository ─────────────────────────
#
# On 15 October a gallery sweep, run from the repository root, left 24
# files there (brief.html, radar.html, matched_jobs.html, empty .jsonl
# outputs): constructing an office constructs its sinks, and some sinks
# create their output file at once, relative to the current directory.
# They were gitignored, so nothing showed it. This check makes the next
# such test fail the run instead of littering silently.

from pathlib import Path as _Path

_REPO_ROOT = _Path(__file__).resolve().parent.parent
_ROOT_FILES_BEFORE: set = set()


def pytest_sessionstart(session):
    _ROOT_FILES_BEFORE.update(p.name for p in _REPO_ROOT.iterdir())


def pytest_sessionfinish(session, exitstatus):
    new = sorted(p.name for p in _REPO_ROOT.iterdir()
                 if p.name not in _ROOT_FILES_BEFORE
                 and p.name not in {".pytest_cache", "__pycache__"})
    if new:
        print(f"\nThe test run wrote into the repository root: {new}. "
              f"A test must write to tmp_path (or chdir there) instead.")
        session.exitstatus = 1
