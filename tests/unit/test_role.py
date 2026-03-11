# tests/unit/test_role.py

"""
Tests for dsl/blocks/role.py

The Role block routes messages to named outputs based on status strings.
Unlike Split (which uses index-based positional outputs), Role lets the
function return an arbitrary list of (message, status) pairs.

Tests are organized in four layers:
    1. Construction    - Role is built correctly; invalid args raise clearly
    2. Status mapping  - status strings map to the right outport names
    3. Function output - fn return values are validated (no network needed)
    4. Network         - Role routes correctly when wired into a full pipeline

Run from DisSysLab root:
    pytest tests/unit/test_role.py -v
"""

import pytest
from queue import SimpleQueue

from dsl.core import STOP
from dsl.blocks.role import Role


# =====================================================================
# Helpers
# =====================================================================

def _wire(role: Role) -> dict:
    """
    Minimal wiring: attach real queues to all ports so run() works.
    Returns {"in_": in_q, "out_0": q0, "out_1": q1, ...}
    """
    in_q = SimpleQueue()
    role.in_q["in_"] = in_q

    out_qs = {}
    for port in role.outports:
        q = SimpleQueue()
        role.out_q[port] = q
        out_qs[port] = q

    return {"in_": in_q, **out_qs}


def _run_with_messages(role: Role, messages: list) -> dict:
    """
    Wire role, feed messages followed by STOP, run synchronously.
    Returns {port: [collected messages]}.
    """
    qs = _wire(role)
    for msg in messages:
        qs["in_"].put(msg)
    qs["in_"].put(STOP)

    role.run()  # synchronous — no thread needed for unit tests

    return {port: _drain(qs[port]) for port in role.outports}


def _drain(q: SimpleQueue) -> list:
    """Collect all non-STOP items currently in a queue (non-blocking)."""
    items = []
    while not q.empty():
        item = q.get_nowait()
        if item is not STOP:
            items.append(item)
    return items


# =====================================================================
# Layer 1: Construction Tests
# =====================================================================

class TestRoleConstruction:
    """Role is built correctly; bad arguments raise clear errors."""

    def test_basic_construction(self):
        role = Role(fn=lambda msg: [(msg, "good")],
                    statuses=["good", "bad"],
                    name="classifier")
        assert role is not None

    def test_inport_is_in_underscore(self):
        """Role always has exactly one inport named 'in_'."""
        role = Role(fn=lambda msg: [], statuses=["a", "b"], name="r")
        assert role.inports == ["in_"]

    def test_outports_match_statuses(self):
        """Two statuses → out_0 and out_1."""
        role = Role(fn=lambda msg: [], statuses=[
                    "interesting", "boring"], name="r")
        assert role.outports == ["out_0", "out_1"]

    def test_three_statuses_three_outports(self):
        role = Role(fn=lambda msg: [],
                    statuses=["positive", "negative", "neutral"],
                    name="sentiment_router")
        assert role.outports == ["out_0", "out_1", "out_2"]

    def test_empty_statuses_defaults_to_all(self):
        """Empty statuses list defaults to ['all'] with single out_0."""
        role = Role(fn=lambda msg: [(msg, "all")], statuses=[], name="r")
        assert role.statuses == ["all"]
        assert role.outports == ["out_0"]

    def test_none_statuses_defaults_to_all(self):
        role = Role(fn=lambda msg: [(msg, "all")], statuses=None, name="r")
        assert role.statuses == ["all"]
        assert role.outports == ["out_0"]

    def test_name_is_required(self):
        """Empty name raises ValueError."""
        with pytest.raises((ValueError, TypeError)):
            Role(fn=lambda msg: [], statuses=["a"], name="")

    def test_fn_must_be_callable(self):
        with pytest.raises(TypeError):
            Role(fn="not_a_function", statuses=["good"], name="r")

    def test_duplicate_statuses_raise(self):
        with pytest.raises(ValueError):
            Role(fn=lambda msg: [], statuses=["good", "good"], name="r")

    def test_statuses_stored_on_instance(self):
        role = Role(fn=lambda msg: [], statuses=["alert", "archive"], name="r")
        assert role.statuses == ["alert", "archive"]


# =====================================================================
# Layer 2: Status Mapping Tests
# =====================================================================

class TestStatusMapping:
    """Status strings map to the correct outport names."""

    def setup_method(self):
        self.role = Role(
            fn=lambda msg: [],
            statuses=["interesting", "boring", "spam"],
            name="r"
        )

    def test_first_status_maps_to_out_0(self):
        assert self.role._status_to_port["interesting"] == "out_0"

    def test_second_status_maps_to_out_1(self):
        assert self.role._status_to_port["boring"] == "out_1"

    def test_third_status_maps_to_out_2(self):
        assert self.role._status_to_port["spam"] == "out_2"

    def test_all_statuses_present_in_map(self):
        for s in ["interesting", "boring", "spam"]:
            assert s in self.role._status_to_port

    def test_map_has_no_extra_entries(self):
        assert len(self.role._status_to_port) == 3


# =====================================================================
# Layer 3: Function Output Tests (no network needed)
# =====================================================================

class TestRoleFunctionOutputs:
    """fn return values drive routing; bad values are caught gracefully."""

    def test_route_to_out_0(self):
        """'interesting' status sends message to out_0."""
        def fn(msg):
            return [(msg, "interesting")]

        role = Role(fn=fn, statuses=["interesting", "boring"], name="r")
        result = _run_with_messages(role, [{"text": "Python rocks"}])

        assert len(result["out_0"]) == 1
        assert result["out_0"][0]["text"] == "Python rocks"
        assert len(result["out_1"]) == 0

    def test_route_to_out_1(self):
        """'boring' status sends message to out_1."""
        def fn(msg):
            return [(msg, "boring")]

        role = Role(fn=fn, statuses=["interesting", "boring"], name="r")
        result = _run_with_messages(role, [{"text": "filler"}])

        assert len(result["out_1"]) == 1
        assert len(result["out_0"]) == 0

    def test_empty_return_drops_message(self):
        """fn returning [] drops the message — nothing arrives anywhere."""
        def fn(msg):
            return []

        role = Role(fn=fn, statuses=["a", "b"], name="r")
        result = _run_with_messages(role, [{"text": "anything"}])

        assert len(result["out_0"]) == 0
        assert len(result["out_1"]) == 0

    def test_one_message_to_multiple_outputs(self):
        """fn can route one message to both outports."""
        def fn(msg):
            return [(msg, "alert"), (msg, "archive")]

        role = Role(fn=fn, statuses=["alert", "archive"], name="r")
        result = _run_with_messages(role, [{"text": "critical"}])

        assert len(result["out_0"]) == 1   # alert
        assert len(result["out_1"]) == 1   # archive

    def test_multiple_messages_routed_independently(self):
        """Each input message is routed on its own merits."""
        def fn(msg):
            if msg["score"] > 0.5:
                return [(msg, "interesting")]
            return [(msg, "boring")]

        role = Role(fn=fn, statuses=["interesting", "boring"], name="r")
        messages = [
            {"score": 0.9},
            {"score": 0.1},
            {"score": 0.8},
        ]
        result = _run_with_messages(role, messages)

        assert len(result["out_0"]) == 2   # scores 0.9 and 0.8
        assert len(result["out_1"]) == 1   # score 0.1

    def test_fn_can_transform_before_routing(self):
        """fn may enrich the message; the enriched version is what gets sent."""
        def fn(msg):
            enriched = {**msg, "processed": True}
            return [(enriched, "done")]

        role = Role(fn=fn, statuses=["done"], name="r")
        result = _run_with_messages(role, [{"text": "raw"}])

        assert result["out_0"][0]["processed"] is True
        assert result["out_0"][0]["text"] == "raw"

    def test_unknown_status_broadcasts_stop(self):
        """fn returning an undeclared status triggers broadcast_stop, not crash."""
        def fn(msg):
            return [(msg, "TYPO_STATUS")]   # not in statuses

        role = Role(fn=fn, statuses=["good", "bad"], name="r")
        qs = _wire(role)
        qs["in_"].put({"text": "hello"})
        qs["in_"].put(STOP)

        role.run()  # should not raise

        # STOP should have propagated to all outports
        for port in role.outports:
            assert qs[port].get() is STOP

    def test_fn_returning_non_list_broadcasts_stop(self):
        """fn returning wrong type triggers broadcast_stop gracefully."""
        def fn(msg):
            return "oops"   # wrong type

        role = Role(fn=fn, statuses=["a"], name="r")
        qs = _wire(role)
        qs["in_"].put({"text": "hello"})
        qs["in_"].put(STOP)

        role.run()

        assert qs["out_0"].get() is STOP

    def test_stop_on_inport_propagates_to_all_outports(self):
        """STOP on in_ propagates to every outport."""
        role = Role(fn=lambda msg: [], statuses=["a", "b", "c"], name="r")
        qs = _wire(role)
        qs["in_"].put(STOP)

        role.run()

        for port in ["out_0", "out_1", "out_2"]:
            assert qs[port].get() is STOP


# =====================================================================
# Layer 4: Full Network Tests
# =====================================================================

class TestRoleInNetwork:
    """Role wires into DisSysLab networks and routes correctly end-to-end."""

    def test_two_way_routing(self):
        """Source → Role sends messages to the right sink."""
        from dsl import network
        from dsl.blocks import Source, Sink

        items = iter([
            {"text": "amazing", "score": 0.9},
            {"text": "terrible", "score": 0.1},
            {"text": "great", "score": 0.8},
            {"text": "awful", "score": 0.2},
        ])

        def categorize(msg):
            if msg["score"] > 0.5:
                return [(msg, "positive")]
            return [(msg, "negative")]

        positive_results = []
        negative_results = []

        src = Source(fn=lambda: next(items, None), name="src")
        router = Role(fn=categorize, statuses=[
                      "positive", "negative"], name="router")
        pos_sink = Sink(fn=positive_results.append, name="pos")
        neg_sink = Sink(fn=negative_results.append, name="neg")

        g = network([
            (src, router),
            (router.out_0, pos_sink),
            (router.out_1, neg_sink),
        ])

        g.run_network()

        assert len(positive_results) == 2
        assert len(negative_results) == 2

    def test_fanout_one_message_to_two_sinks(self):
        """fn returning two pairs sends one message to both sinks."""
        from dsl import network
        from dsl.blocks import Source, Sink

        items = iter([{"text": "breaking news", "score": 0.95}])

        def broadcast(msg):
            return [(msg, "alert"), (msg, "archive")]

        alert_results = []
        archive_results = []

        src = Source(fn=lambda: next(items, None), name="src")
        broadcaster = Role(fn=broadcast, statuses=[
                           "alert", "archive"], name="b")
        alert_sink = Sink(fn=alert_results.append, name="alert")
        archive_sink = Sink(fn=archive_results.append, name="archive")

        g = network([
            (src, broadcaster),
            (broadcaster.out_0, alert_sink),
            (broadcaster.out_1, archive_sink),
        ])

        g.run_network()

        assert len(alert_results) == 1
        assert len(archive_results) == 1

    def test_role_after_transform(self):
        """Transform → Role: enriched messages are routed correctly."""
        from dsl import network
        from dsl.blocks import Source, Transform, Sink

        items = iter([
            {"text": "Python 3.13 released", "score": 0.8},
            {"text": "Stock market falls", "score": 0.2},
        ])

        def add_label(msg):
            return {**msg, "label": "pos" if msg["score"] > 0.5 else "neg"}

        def route_by_label(msg):
            return [(msg, msg["label"])]

        pos, neg = [], []

        src = Source(fn=lambda: next(items, None), name="src")
        labeler = Transform(fn=add_label, name="labeler")
        router = Role(fn=route_by_label, statuses=[
                      "pos", "neg"], name="router")
        pos_sink = Sink(fn=pos.append, name="pos")
        neg_sink = Sink(fn=neg.append, name="neg")

        g = network([
            (src, labeler),
            (labeler, router),
            (router.out_0, pos_sink),
            (router.out_1, neg_sink),
        ])

        g.run_network()

        assert len(pos) == 1
        assert pos[0]["label"] == "pos"
        assert len(neg) == 1
        assert neg[0]["label"] == "neg"

    def test_filter_via_empty_return(self):
        """Role returning [] for some messages drops them — fewer results downstream."""
        from dsl import network
        from dsl.blocks import Source, Sink

        items = iter([
            {"score": 0.9},   # interesting
            {"score": 0.05},  # noise — dropped
            {"score": 0.8},   # interesting
            {"score": 0.03},  # noise — dropped
        ])

        def filter_noise(msg):
            if msg["score"] < 0.1:
                return []   # drop
            return [(msg, "signal")]

        results = []

        src = Source(fn=lambda: next(items, None), name="src")
        noise_filter = Role(fn=filter_noise, statuses=[
                            "signal"], name="filter")
        sink = Sink(fn=results.append, name="sink")

        g = network([
            (src, noise_filter),
            (noise_filter.out_0, sink),
        ])

        g.run_network()

        assert len(results) == 2
        assert all(r["score"] >= 0.1 for r in results)
