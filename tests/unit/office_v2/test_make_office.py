"""Unit tests for ``office_v2.make_office``.

The central guarantee: ``make_office`` is the inverse of
``parse_office_dir``. For every well-formed ``OfficeSpec`` we
construct, ``parse_office_dir(make_office(target, spec, {}))``
should yield a spec structurally equal to the original.

Other tests cover error conditions and edge cases.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from dissyslab.office_v2 import (
    ConnectionStmt,
    Endpoint,
    EXTERNAL,
    OfficeSpec,
    RoleRef,
    SinkSpec,
    SourceSpec,
    parse_office_dir,
)
from dissyslab.office_v2.make_office import make_office


# ── Round-trip tests ──────────────────────────────────────────────────


class TestRoundTrip:
    def test_minimal_closed_office(self, tmp_path):
        spec = OfficeSpec(
            name="tiny",
            sources=(SourceSpec(name="hacker_news"),),
            sinks=(SinkSpec(name="discard"),),
            agents=(RoleRef(agent_name="Alex", role_name="analyst"),),
            connections=(
                ConnectionStmt(
                    source=Endpoint("hacker_news", "destination"),
                    destinations=(Endpoint("Alex", "in_"),),
                ),
                ConnectionStmt(
                    source=Endpoint("Alex", "briefing"),
                    destinations=(Endpoint("discard", "in_"),),
                ),
            ),
        )
        target = tmp_path / "tiny_office"

        result = make_office(target, spec, roles_lib={})

        assert result == target
        assert (target / "office.md").exists()

        parsed = parse_office_dir(target)
        assert parsed.name == spec.name
        assert parsed.sources == spec.sources
        assert parsed.sinks == spec.sinks
        assert parsed.agents == spec.agents
        assert parsed.connections == spec.connections

    def test_source_with_kwargs(self, tmp_path):
        spec = OfficeSpec(
            name="hn_briefing",
            sources=(
                SourceSpec(
                    name="hacker_news",
                    args=(("max_articles", 10), ("poll_interval", 600)),
                ),
            ),
            sinks=(SinkSpec(name="console_printer"),),
            agents=(RoleRef(agent_name="Alex", role_name="analyst"),),
            connections=(
                ConnectionStmt(
                    source=Endpoint("hacker_news", "destination"),
                    destinations=(Endpoint("Alex", "in_"),),
                ),
                ConnectionStmt(
                    source=Endpoint("Alex", "briefing"),
                    destinations=(Endpoint("console_printer", "in_"),),
                ),
            ),
        )
        target = tmp_path / "hn"
        make_office(target, spec, roles_lib={})
        parsed = parse_office_dir(target)
        assert parsed.sources == spec.sources

    def test_sink_with_kwargs(self, tmp_path):
        spec = OfficeSpec(
            name="recorded",
            sources=(SourceSpec(name="hacker_news"),),
            sinks=(
                SinkSpec(
                    name="jsonl_recorder",
                    args=(("path", "out.jsonl"),),
                ),
            ),
            agents=(RoleRef(agent_name="Alex", role_name="analyst"),),
            connections=(
                ConnectionStmt(
                    source=Endpoint("hacker_news", "destination"),
                    destinations=(Endpoint("Alex", "in_"),),
                ),
                ConnectionStmt(
                    source=Endpoint("Alex", "briefing"),
                    destinations=(Endpoint("jsonl_recorder", "in_"),),
                ),
            ),
        )
        target = tmp_path / "rec"
        make_office(target, spec, roles_lib={})
        parsed = parse_office_dir(target)
        assert parsed.sinks == spec.sinks

    def test_open_office_with_inputs_outputs(self, tmp_path):
        spec = OfficeSpec(
            name="open_pipeline",
            inputs=("article_in",),
            outputs=("article_out",),
            agents=(RoleRef(agent_name="Alex", role_name="analyst"),),
            connections=(
                ConnectionStmt(
                    source=Endpoint(EXTERNAL, "article_in"),
                    destinations=(Endpoint("Alex", "in_"),),
                ),
                ConnectionStmt(
                    source=Endpoint("Alex", "out"),
                    destinations=(Endpoint(EXTERNAL, "article_out"),),
                ),
            ),
        )
        target = tmp_path / "open"
        make_office(target, spec, roles_lib={})
        parsed = parse_office_dir(target)
        assert parsed.inputs == spec.inputs
        assert parsed.outputs == spec.outputs
        assert parsed.agents == spec.agents
        assert parsed.connections == spec.connections

    def test_fork_to_multiple_destinations(self, tmp_path):
        spec = OfficeSpec(
            name="forking",
            sources=(SourceSpec(name="hacker_news"),),
            sinks=(SinkSpec(name="discard"),),
            agents=(
                RoleRef(agent_name="Alex", role_name="analyst"),
                RoleRef(agent_name="Morgan", role_name="editor"),
            ),
            connections=(
                ConnectionStmt(
                    source=Endpoint("hacker_news", "destination"),
                    destinations=(
                        Endpoint("Alex", "in_"),
                        Endpoint("Morgan", "in_"),
                        Endpoint("discard", "in_"),
                    ),
                ),
            ),
        )
        target = tmp_path / "fork"
        make_office(target, spec, roles_lib={})
        parsed = parse_office_dir(target)
        assert parsed.connections == spec.connections

    def test_subroutine_office_reference(self, tmp_path):
        spec = OfficeSpec(
            name="parent",
            sources=(SourceSpec(name="hacker_news"),),
            sinks=(SinkSpec(name="discard"),),
            agents=(
                RoleRef(
                    agent_name="news",
                    role_name="news_monitor",
                    path="../news_monitor",
                ),
            ),
            connections=(
                ConnectionStmt(
                    source=Endpoint("hacker_news", "destination"),
                    destinations=(Endpoint("news", "article_in"),),
                ),
                ConnectionStmt(
                    source=Endpoint("news", "article_out"),
                    destinations=(Endpoint("discard", "in_"),),
                ),
            ),
        )
        target = tmp_path / "parent_office"
        make_office(target, spec, roles_lib={})
        parsed = parse_office_dir(target)
        assert parsed.agents == spec.agents
        assert parsed.connections == spec.connections

    def test_explicit_named_dest_port(self, tmp_path):
        # Sub-office input port: 'X is news_monitor's article_in.'
        spec = OfficeSpec(
            name="named_port",
            sources=(SourceSpec(name="hacker_news"),),
            sinks=(SinkSpec(name="discard"),),
            agents=(
                RoleRef(
                    agent_name="sub",
                    role_name="news_monitor",
                    path="../news_monitor",
                ),
            ),
            connections=(
                ConnectionStmt(
                    source=Endpoint("hacker_news", "destination"),
                    destinations=(Endpoint("sub", "article_in"),),
                ),
                ConnectionStmt(
                    source=Endpoint("sub", "article_out"),
                    destinations=(Endpoint("discard", "in_"),),
                ),
            ),
        )
        target = tmp_path / "np"
        make_office(target, spec, roles_lib={})
        parsed = parse_office_dir(target)
        assert parsed.connections == spec.connections


# ── Error / edge cases ────────────────────────────────────────────────


class TestErrors:
    def test_target_dir_exists_raises(self, tmp_path):
        target = tmp_path / "already_here"
        target.mkdir()

        spec = OfficeSpec(
            name="x",
            sources=(SourceSpec(name="hacker_news"),),
            sinks=(SinkSpec(name="discard"),),
            agents=(RoleRef(agent_name="Alex", role_name="analyst"),),
            connections=(
                ConnectionStmt(
                    source=Endpoint("hacker_news", "destination"),
                    destinations=(Endpoint("Alex", "in_"),),
                ),
                ConnectionStmt(
                    source=Endpoint("Alex", "out"),
                    destinations=(Endpoint("discard", "in_"),),
                ),
            ),
        )
        with pytest.raises(FileExistsError, match="already exists"):
            make_office(target, spec, roles_lib={})

    def test_creates_parent_dirs(self, tmp_path):
        # Nested target_dir under non-existent parents.
        target = tmp_path / "a" / "b" / "c" / "office"

        spec = OfficeSpec(
            name="deep",
            sources=(SourceSpec(name="hacker_news"),),
            sinks=(SinkSpec(name="discard"),),
            agents=(RoleRef(agent_name="Alex", role_name="analyst"),),
            connections=(
                ConnectionStmt(
                    source=Endpoint("hacker_news", "destination"),
                    destinations=(Endpoint("Alex", "in_"),),
                ),
                ConnectionStmt(
                    source=Endpoint("Alex", "out"),
                    destinations=(Endpoint("discard", "in_"),),
                ),
            ),
        )
        make_office(target, spec, roles_lib={})
        assert target.exists()
        assert (target / "office.md").exists()


# ── Returned path matches input ───────────────────────────────────────


class TestReturnValue:
    def test_returns_target_dir(self, tmp_path):
        target = tmp_path / "ret"
        spec = OfficeSpec(
            name="r",
            sources=(SourceSpec(name="hacker_news"),),
            sinks=(SinkSpec(name="discard"),),
            agents=(RoleRef(agent_name="Alex", role_name="analyst"),),
            connections=(
                ConnectionStmt(
                    source=Endpoint("hacker_news", "destination"),
                    destinations=(Endpoint("Alex", "in_"),),
                ),
                ConnectionStmt(
                    source=Endpoint("Alex", "out"),
                    destinations=(Endpoint("discard", "in_"),),
                ),
            ),
        )
        result = make_office(target, spec, roles_lib={})
        assert result == target
        assert isinstance(result, Path)
