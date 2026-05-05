"""Unit tests for OfficeSpec and its companion small dataclasses.

These tests focus on the type-level invariants enforced in
``__post_init__``. Parser-level tests live in ``test_parser.py``.
"""
from __future__ import annotations

import pytest

from dissyslab.office_v2 import (
    ConnectionStmt,
    Endpoint,
    EXTERNAL,
    OfficeSpec,
    RoleRef,
    SinkSpec,
    SourceSpec,
)


# ── SourceSpec / SinkSpec ──────────────────────────────────────────────


class TestSourceSpec:
    def test_minimal(self):
        s = SourceSpec(name="rss")
        assert s.name == "rss"
        assert s.args == ()

    def test_with_args(self):
        s = SourceSpec(name="rss", args=(("max", 5),))
        assert s.args == (("max", 5),)

    def test_args_coerced_to_tuple(self):
        s = SourceSpec(name="rss", args=[("max", 5), ("poll", 60)])
        assert s.args == (("max", 5), ("poll", 60))
        assert isinstance(s.args, tuple)

    def test_empty_name_rejected(self):
        with pytest.raises(ValueError):
            SourceSpec(name="")

    def test_external_name_rejected(self):
        with pytest.raises(ValueError, match="reserved"):
            SourceSpec(name=EXTERNAL)

    def test_empty_arg_key_rejected(self):
        with pytest.raises(ValueError, match="empty key"):
            SourceSpec(name="rss", args=(("", 5),))

    def test_hashable(self):
        s1 = SourceSpec(name="rss", args=(("k", 1),))
        s2 = SourceSpec(name="rss", args=(("k", 1),))
        assert hash(s1) == hash(s2)
        assert {s1, s2} == {s1}


class TestSinkSpec:
    def test_minimal(self):
        s = SinkSpec(name="printer")
        assert s.name == "printer"

    def test_external_name_rejected(self):
        with pytest.raises(ValueError, match="reserved"):
            SinkSpec(name=EXTERNAL)


# ── RoleRef ────────────────────────────────────────────────────────────


class TestRoleRef:
    def test_leaf_role(self):
        r = RoleRef(agent_name="Susan", role_name="editor")
        assert r.agent_name == "Susan"
        assert r.role_name == "editor"
        assert r.path is None
        # Convenience alias for downstream code that used to read .name
        assert r.name == "Susan"

    def test_sub_office_with_path(self):
        r = RoleRef(
            agent_name="news_monitor",
            role_name="news_monitor",
            path="../news_monitor",
        )
        assert r.path == "../news_monitor"

    def test_empty_agent_name_rejected(self):
        with pytest.raises(ValueError):
            RoleRef(agent_name="", role_name="editor")

    def test_external_agent_name_rejected(self):
        with pytest.raises(ValueError, match="reserved"):
            RoleRef(agent_name=EXTERNAL, role_name="editor")

    def test_empty_role_name_rejected(self):
        with pytest.raises(ValueError, match="empty role_name"):
            RoleRef(agent_name="X", role_name="")

    def test_empty_path_rejected(self):
        with pytest.raises(ValueError, match="empty path"):
            RoleRef(agent_name="X", role_name="r", path="")

    def test_hashable(self):
        r1 = RoleRef(agent_name="X", role_name="r")
        r2 = RoleRef(agent_name="X", role_name="r")
        assert hash(r1) == hash(r2)
        assert {r1, r2} == {r1}


# ── Endpoint ───────────────────────────────────────────────────────────


class TestEndpoint:
    def test_basic(self):
        e = Endpoint(name="Alex", port="briefing")
        assert e.name == "Alex"
        assert e.port == "briefing"

    def test_external(self):
        e = Endpoint(name=EXTERNAL, port="article_in")
        assert e.name == EXTERNAL
        assert e.port == "article_in"

    def test_empty_name_rejected(self):
        with pytest.raises(ValueError):
            Endpoint(name="", port="p")

    def test_empty_port_rejected(self):
        with pytest.raises(ValueError):
            Endpoint(name="Alex", port="")

    def test_hashable(self):
        e1 = Endpoint(name="Alex", port="briefing")
        e2 = Endpoint(name="Alex", port="briefing")
        assert hash(e1) == hash(e2)
        assert {e1, e2} == {e1}


# ── ConnectionStmt ─────────────────────────────────────────────────────


class TestConnectionStmt:
    def test_one_destination(self):
        c = ConnectionStmt(
            source=Endpoint(name="Alex", port="briefing"),
            destinations=(Endpoint(name="printer", port="in_"),),
        )
        assert c.source.name == "Alex"
        assert len(c.destinations) == 1

    def test_two_destinations(self):
        c = ConnectionStmt(
            source=Endpoint(name="Susan", port="archivist"),
            destinations=(
                Endpoint(name="A", port="in_"),
                Endpoint(name="B", port="in_"),
            ),
        )
        assert len(c.destinations) == 2

    def test_empty_destinations_rejected(self):
        with pytest.raises(ValueError, match="no destinations"):
            ConnectionStmt(
                source=Endpoint(name="Alex", port="b"),
                destinations=(),
            )

    def test_destinations_coerced_to_tuple(self):
        c = ConnectionStmt(
            source=Endpoint(name="Alex", port="briefing"),
            destinations=[
                Endpoint(name="A", port="in_"),
                Endpoint(name="B", port="in_"),
            ],
        )
        assert isinstance(c.destinations, tuple)

    def test_non_endpoint_source_rejected(self):
        with pytest.raises(TypeError):
            ConnectionStmt(
                source="Alex",  # type: ignore[arg-type]
                destinations=(Endpoint(name="A", port="in_"),),
            )

    def test_non_endpoint_destination_rejected(self):
        with pytest.raises(TypeError):
            ConnectionStmt(
                source=Endpoint(name="Alex", port="b"),
                destinations=("X",),  # type: ignore[arg-type]
            )


# ── OfficeSpec ─────────────────────────────────────────────────────────


class TestOfficeSpec:
    def test_minimal_closed_office(self):
        spec = OfficeSpec(
            name="demo",
            sources=(SourceSpec(name="rss"),),
            sinks=(SinkSpec(name="printer"),),
            agents=(
                RoleRef(agent_name="Alex", role_name="analyst"),
            ),
        )
        assert spec.name == "demo"
        assert not spec.is_open()
        assert spec.agent_names() == ("Alex",)

    def test_open_office(self):
        spec = OfficeSpec(
            name="open_demo",
            inputs=("feed",),
            outputs=("done",),
            agents=(
                RoleRef(agent_name="A", role_name="analyst"),
            ),
        )
        assert spec.is_open()

    def test_external_name_rejected(self):
        with pytest.raises(ValueError, match="reserved"):
            OfficeSpec(name=EXTERNAL)

    def test_duplicate_input_name_rejected(self):
        with pytest.raises(ValueError, match="duplicates"):
            OfficeSpec(name="o", inputs=("x", "x"))

    def test_name_collision_source_and_agent(self):
        with pytest.raises(ValueError, match="declared as both"):
            OfficeSpec(
                name="o",
                sources=(SourceSpec(name="conflict"),),
                agents=(
                    RoleRef(agent_name="conflict", role_name="analyst"),
                ),
            )

    def test_name_collision_source_and_sink(self):
        with pytest.raises(ValueError, match="declared as both"):
            OfficeSpec(
                name="o",
                sources=(SourceSpec(name="x"),),
                sinks=(SinkSpec(name="x"),),
            )

    def test_agents_uniform_role_refs(self):
        spec = OfficeSpec(
            name="o",
            agents=(
                RoleRef(agent_name="Alex", role_name="analyst"),
                RoleRef(
                    agent_name="news_monitor",
                    role_name="news_monitor",
                    path="../news_monitor",
                ),
            ),
        )
        assert spec.agent_names() == ("Alex", "news_monitor")
        office_refs = spec.office_refs()
        assert len(office_refs) == 1
        assert office_refs[0].agent_name == "news_monitor"
        assert office_refs[0].path == "../news_monitor"

    def test_agents_must_be_role_refs(self):
        with pytest.raises(TypeError, match="RoleRef"):
            OfficeSpec(
                name="o",
                agents=("not-an-agent",),  # type: ignore[arg-type]
            )

    def test_role_ref_collides_with_source(self):
        with pytest.raises(ValueError, match="declared as both"):
            OfficeSpec(
                name="o",
                sources=(SourceSpec(name="dup"),),
                agents=(
                    RoleRef(
                        agent_name="dup", role_name="r", path="/p"
                    ),
                ),
            )

    def test_hashable(self):
        a = RoleRef(agent_name="Alex", role_name="analyst")
        spec1 = OfficeSpec(name="o", agents=(a,))
        spec2 = OfficeSpec(name="o", agents=(a,))
        assert hash(spec1) == hash(spec2)

    def test_iterables_coerced_to_tuples(self):
        spec = OfficeSpec(
            name="o",
            inputs=["a"],
            agents=[
                RoleRef(agent_name="A", role_name="analyst"),
            ],
        )
        assert isinstance(spec.inputs, tuple)
        assert isinstance(spec.agents, tuple)
