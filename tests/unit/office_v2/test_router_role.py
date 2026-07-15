"""
Unit tests for ``router_role`` — the post-merge routing primitive
(added alongside NetworkOfThought #189).

A router receives one message at a time and, for each of its routes,
decides whether to emit a copy on that route's outport. Routes are
independent: one message can fire several outports; a message matching
no route is dropped.
"""

from __future__ import annotations

import pytest

from dissyslab.blocks.role import Role
from dissyslab.office.library import (
    AgentRoleEntry,
    PARAMETERIZED_LIBRARY,
    router_role,
)


def test_registered_in_parameterized_library():
    assert PARAMETERIZED_LIBRARY.get("router") is router_role


def test_single_route_is_a_filter():
    entry = router_role(
        [{"outport": "critical", "field": "severity", "equals": "critical"}]
    )
    assert isinstance(entry, AgentRoleEntry)
    assert entry.name == "router"
    assert entry.in_ports == ("in_",)
    assert entry.out_ports == ("critical",)

    agent = entry()
    # One semantic outport → runtime "out_" (framework single-out rule).
    assert agent.outports == ["out_"]

    fn = agent._fn
    assert fn({"severity": "critical", "x": 1}) == [
        ({"severity": "critical", "x": 1}, "critical")
    ]
    # Non-matching message is dropped.
    assert fn({"severity": "low"}) == []


def test_unconditional_route_forwards_everything():
    entry = router_role([{"outport": "out"}])  # no field → always fires
    fn = entry()._fn
    assert fn({"anything": 1}) == [({"anything": 1}, "out")]
    assert fn({}) == [({}, "out")]


def test_multi_outport_indexing_matches_runtime_convention():
    entry = router_role(
        [
            {"outport": "a", "field": "k", "equals": 1},
            {"outport": "b", "field": "k", "equals": 2},
        ]
    )
    assert entry.out_ports == ("a", "b")
    agent = entry()
    # Multiple semantic outports → out_0/out_1, in declared order.
    assert agent.outports == ["out_0", "out_1"]
    assert agent._status_to_port == {"a": "out_0", "b": "out_1"}
    assert isinstance(agent, Role)

    fn = agent._fn
    assert fn({"k": 1}) == [({"k": 1}, "a")]
    assert fn({"k": 2}) == [({"k": 2}, "b")]
    assert fn({"k": 3}) == []


def test_a_message_can_match_several_routes():
    entry = router_role(
        [
            {"outport": "all"},  # unconditional
            {"outport": "hot", "field": "temp", "equals": "high"},
        ]
    )
    fn = entry()._fn
    out = fn({"temp": "high"})
    assert ({"temp": "high"}, "all") in out
    assert ({"temp": "high"}, "hot") in out
    assert len(out) == 2


def test_empty_routes_rejected():
    with pytest.raises(ValueError):
        router_role([])


def test_duplicate_outports_rejected():
    with pytest.raises(ValueError):
        router_role(
            [{"outport": "x", "field": "a", "equals": 1},
             {"outport": "x", "field": "b", "equals": 2}]
        )


def test_route_needs_outport():
    with pytest.raises(ValueError):
        router_role([{"field": "a", "equals": 1}])
