"""Unit tests for the deduplicator fn_lib entry.

The deduplicator is the canonical fn_lib entry — drop messages whose
chosen field has been seen before. Tests cover:

* Initial-state factory produces a fresh, empty seen-set.
* Per-message function passes first sighting, drops repeats.
* Custom ``by=`` keys other than ``url`` work.
* Malformed inputs (non-dict, missing key) are dropped silently.
* End-to-end behaviour through a Transform block matches the direct
  function call — verifies the fn signature lines up with Transform's
  call shape.
"""
from __future__ import annotations

import pytest

from dissyslab import network
from dissyslab.blocks import Sink, Source, Transform
from dissyslab.fn_lib import FN_LIB
from dissyslab.fn_lib.dedup import deduplicator, deduplicator_initial_state


# ── Direct function tests ─────────────────────────────────────────────


class TestDeduplicatorFunction:

    def test_first_sighting_passes_through(self):
        state = deduplicator_initial_state()
        msg = {"url": "http://a.com", "title": "A"}
        assert deduplicator(msg, state=state, by="url") is msg

    def test_repeat_is_dropped(self):
        state = deduplicator_initial_state()
        msg = {"url": "http://a.com"}
        deduplicator(msg, state=state, by="url")
        assert deduplicator(msg, state=state, by="url") is None

    def test_distinct_urls_pass(self):
        state = deduplicator_initial_state()
        a = {"url": "http://a.com"}
        b = {"url": "http://b.com"}
        assert deduplicator(a, state=state, by="url") is a
        assert deduplicator(b, state=state, by="url") is b

    def test_custom_field(self):
        state = deduplicator_initial_state()
        m1 = {"id": 42, "title": "First"}
        m2 = {"id": 42, "title": "Same id, different title"}
        m3 = {"id": 43, "title": "Different id"}
        assert deduplicator(m1, state=state, by="id") is m1
        assert deduplicator(m2, state=state, by="id") is None
        assert deduplicator(m3, state=state, by="id") is m3

    def test_non_dict_input_dropped(self):
        state = deduplicator_initial_state()
        assert deduplicator("not a dict", state=state, by="url") is None
        assert deduplicator(42, state=state, by="url") is None
        assert deduplicator(None, state=state, by="url") is None

    def test_missing_key_dropped(self):
        state = deduplicator_initial_state()
        assert deduplicator({"title": "no url"}, state=state, by="url") is None

    def test_state_grows_with_distinct_inputs(self):
        state = deduplicator_initial_state()
        for url in ["http://a.com", "http://b.com", "http://c.com"]:
            deduplicator({"url": url}, state=state, by="url")
        assert state == {
            "seen": {"http://a.com", "http://b.com", "http://c.com"}
        }


# ── Registry tests ────────────────────────────────────────────────────


class TestDeduplicatorRegistration:

    def test_registered_under_canonical_name(self):
        assert "deduplicator" in FN_LIB

    def test_entry_fields_are_sane(self):
        entry = FN_LIB["deduplicator"]
        assert entry.name == "deduplicator"
        assert callable(entry.fn)
        assert callable(entry.initial_state)
        assert entry.description  # non-empty


# ── End-to-end through a Transform ────────────────────────────────────


def _collect_sink():
    results = []
    sink = Sink(fn=results.append)
    return sink, results


def _make_source(items):
    data = list(items)
    index = [0]

    def fn():
        if index[0] >= len(data):
            return None
        val = data[index[0]]
        index[0] += 1
        return val

    return Source(fn=fn)


class TestDeduplicatorThroughTransform:
    """Wire the deduplicator into a Transform — same path the compiler
    will take for ``Sasha is a deduplicator(by="url").``."""

    def test_dedupes_through_transform(self):
        entry = FN_LIB["deduplicator"]
        src = _make_source([
            {"url": "http://a.com", "title": "A"},
            {"url": "http://b.com", "title": "B"},
            {"url": "http://a.com", "title": "A repeat"},
            {"url": "http://c.com", "title": "C"},
            {"url": "http://b.com", "title": "B repeat"},
        ])
        sasha = Transform(
            fn=entry.fn,
            params={"by": "url"},
            state=entry.initial_state(),
            name="Sasha",
        )
        sink, results = _collect_sink()
        g = network([(src, sasha), (sasha, sink)])
        g.run_network(timeout=5)

        assert [r["url"] for r in results] == [
            "http://a.com", "http://b.com", "http://c.com",
        ]
        # State on Sasha reflects every distinct URL seen.
        assert sasha.state == {
            "seen": {"http://a.com", "http://b.com", "http://c.com"}
        }

    def test_two_dedupers_independent(self):
        """Two Transforms built from the same entry don't share state."""
        entry = FN_LIB["deduplicator"]
        sasha = Transform(
            fn=entry.fn,
            params={"by": "url"},
            state=entry.initial_state(),
            name="Sasha",
        )
        robin = Transform(
            fn=entry.fn,
            params={"by": "url"},
            state=entry.initial_state(),
            name="Robin",
        )
        # Mutate Sasha's seen set; Robin's must remain empty.
        sasha._state["seen"].add("http://shared.com")
        assert robin._state == {"seen": set()}
