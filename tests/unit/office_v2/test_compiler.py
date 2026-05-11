"""Unit tests for ``office_v2.compiler``.

The compiler walks an OfficeSpec + role library and produces a runtime
``dissyslab.network.Network``. These tests cover the wiring decisions
the compiler makes — block construction, semantic-to-runtime port
translation, sub-office recursion (both via explicit
``OfficeRoleEntry`` and via the inline ``office at <path>`` sugar),
and library-override scoping. We do not actually run the compiled
networks (no threads, no LLM calls); we just assert on the shape
``Network.compile()`` produces.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from dissyslab.backends import register_backend
from dissyslab.network import Network
from dissyslab.office_v2 import (
    AgentRoleEntry,
    OfficeRoleEntry,
    nl_role,
)
from dissyslab.office_v2.compiler import (
    CompileError,
    CompileWarning,
    compile_office,
)


# ── Helpers ───────────────────────────────────────────────────────────


class _StubBackend:
    """Echo backend that returns a fixed JSON reply for every call."""

    def __init__(self, reply: str):
        self.reply = reply

    def complete(self, *, system, user, max_tokens=1024,
                 temperature=1.0, model=None) -> str:
        return self.reply


def _register_stub(name: str, reply: str) -> None:
    register_backend(name, lambda: _StubBackend(reply))


def _stub_default_send_to(out_port: str = "brief") -> str:
    return json.dumps({"send_to": out_port, "text": "ok"})


def _write_office_md(office_dir: Path, body: str) -> None:
    office_dir.mkdir(parents=True, exist_ok=True)
    (office_dir / "office.md").write_text(body)


def _write_role_md(office_dir: Path, role_name: str, prompt_body: str) -> None:
    """Drop a prompt file into ``<office_dir>/roles/`` for nl_role pickup."""
    roles_dir = office_dir / "roles"
    roles_dir.mkdir(parents=True, exist_ok=True)
    (roles_dir / f"{role_name}.md").write_text(prompt_body)


# ── Closed-office happy path ──────────────────────────────────────────


class TestClosedOffice:
    def test_minimal_source_role_sink(self, tmp_path):
        _register_stub("stub-c", _stub_default_send_to("brief"))
        _write_office_md(tmp_path, (
            "# Office: tiny\n\n"
            "Sources: hacker_news\n"
            "Sinks: discard\n\n"
            "Agents:\n"
            "Alex is an analyst.\n\n"
            "Connections:\n"
            "hacker_news's destination is Alex.\n"
            "Alex's brief is discard.\n"
        ))
        # Override library so we don't need a real LLM.
        analyst = nl_role("You analyse. Send to brief.", AI="stub-c")
        net, warnings = compile_office(
            tmp_path, library={"analyst": analyst}
        )
        assert isinstance(net, Network)
        assert warnings == []
        assert net.name == "tiny"
        assert set(net.blocks) == {"hacker_news", "Alex", "discard"}

    def test_source_port_translates_to_out_underscore(self, tmp_path):
        _register_stub("stub-st", _stub_default_send_to("brief"))
        _write_office_md(tmp_path, (
            "# Office: t\n\n"
            "Sources: hacker_news\n"
            "Sinks: discard\n\n"
            "Agents:\nAlex is an analyst.\n\n"
            "Connections:\n"
            "hacker_news's destination is Alex.\n"
            "Alex's brief is discard.\n"
        ))
        net, _ = compile_office(
            tmp_path,
            library={
                "analyst": nl_role(
                    "You analyse. Send to brief.", AI="stub-st"
                )
            },
        )
        # The user wrote "destination" (English) for the source's
        # port; the runtime port is "out_".
        edges = [c for c in net.connections if c[0] == "hacker_news"]
        assert edges == [("hacker_news", "out_", "Alex", "in_")]

    def test_semantic_outport_translates_to_indexed(self, tmp_path):
        _register_stub("stub-idx", _stub_default_send_to("brief"))
        _write_office_md(tmp_path, (
            "# Office: t\n\n"
            "Sources: hacker_news\n"
            "Sinks: discard\n\n"
            "Agents:\nAlex is an analyst.\n\n"
            "Connections:\n"
            "hacker_news's destination is Alex.\n"
            "Alex's brief is discard.\n"
        ))
        net, _ = compile_office(
            tmp_path,
            library={
                "analyst": nl_role(
                    "You analyse. Send to brief or to skip.",
                    AI="stub-idx",
                )
            },
        )
        # "brief" is the 0-th declared outport → out_0.
        alex_edges = [c for c in net.connections if c[0] == "Alex"]
        assert alex_edges == [("Alex", "out_0", "discard", "in_")]


# ── Open office with Inputs / Outputs ─────────────────────────────────


class TestOpenOffice:
    def test_external_in_and_out(self, tmp_path):
        _register_stub("stub-open", _stub_default_send_to("brief"))
        _write_office_md(tmp_path, (
            "# Office: o\n\n"
            "Inputs: feed\n"
            "Outputs: report\n\n"
            "Agents:\nAlex is an analyst.\n\n"
            "Connections:\n"
            "feed's destination is Alex.\n"
            "Alex's brief is report.\n"
        ))
        net, _ = compile_office(
            tmp_path,
            library={
                "analyst": nl_role(
                    "You analyse. Send to brief.", AI="stub-open"
                )
            },
        )
        assert net.inports == ["feed"]
        assert net.outports == ["report"]
        # External wiring on both sides survives translation.
        # Single-status role's outport is "out_" (not "out_0").
        assert ("external", "feed", "Alex", "in_") in net.connections
        assert ("Alex", "out_", "external", "report") in net.connections


# ── Sub-office recursion ──────────────────────────────────────────────


class TestSubOffices:
    def _build_news_monitor(self, root: Path) -> Path:
        """Create an open sub-office at root/news_monitor/."""
        sub = root / "news_monitor"
        _write_office_md(sub, (
            "# Office: news_monitor\n\n"
            "Inputs: article_in\n"
            "Outputs: article_out\n\n"
            "Agents:\nMorgan is an analyst.\n\n"
            "Connections:\n"
            "article_in's destination is Morgan.\n"
            "Morgan's brief is article_out.\n"
        ))
        # Sub-office's own library
        _write_role_md(
            sub, "analyst", "You analyse. Send to brief."
        )
        return sub

    def test_explicit_office_role_entry(self, tmp_path):
        _register_stub("stub-sub-explicit", _stub_default_send_to("brief"))
        # Force the sub-office's library to use our stub backend:
        # by writing a roles/analyst.py with an explicit entry.
        sub = self._build_news_monitor(tmp_path)
        # Replace the .md with an explicit AI=stub binding via .py
        (sub / "roles" / "analyst.md").unlink()
        (sub / "roles" / "analyst.py").write_text(
            "from dissyslab.office_v2 import nl_role\n"
            "role = nl_role('You analyse. Send to brief.', "
            "AI='stub-sub-explicit')\n"
        )

        # Parent office that wires news_monitor as a sub-office.
        _write_office_md(tmp_path, (
            "# Office: parent\n\n"
            "Sources: hacker_news\n"
            "Sinks: discard\n\n"
            "Agents:\nfeeder is an office.\n\n"
            "Connections:\n"
            "hacker_news's destination is feeder's article_in.\n"
            "feeder's article_out is discard.\n"
        ))
        # Library entry pointing at the sub-office on disk.
        net, warnings = compile_office(
            tmp_path,
            library={
                "office": OfficeRoleEntry(
                    name="news_monitor", path="news_monitor"
                ),
            },
        )
        assert warnings == []
        assert "feeder" in net.blocks
        assert isinstance(net.blocks["feeder"], Network)
        # Sub-office has the right external ports
        assert net.blocks["feeder"].inports == ["article_in"]
        assert net.blocks["feeder"].outports == ["article_out"]

    def test_inline_path_sugar_compiles_and_warns(self, tmp_path):
        _register_stub("stub-sugar", _stub_default_send_to("brief"))
        sub = self._build_news_monitor(tmp_path)
        # Replace the .md with explicit AI=stub binding so the
        # sub-office's library uses our stub backend.
        (sub / "roles" / "analyst.md").unlink()
        (sub / "roles" / "analyst.py").write_text(
            "from dissyslab.office_v2 import nl_role\n"
            "role = nl_role('You analyse. Send to brief.', "
            "AI='stub-sugar')\n"
        )

        # Legacy form: "X is an office at <path>." — no library entry.
        _write_office_md(tmp_path, (
            "# Office: parent\n\n"
            "Sources: hacker_news\n"
            "Sinks: discard\n\n"
            "Agents:\nfeeder is an office at news_monitor.\n\n"
            "Connections:\n"
            "hacker_news's destination is feeder's article_in.\n"
            "feeder's article_out is discard.\n"
        ))
        # Empty library — relies entirely on inline-path sugar.
        net, warnings = compile_office(tmp_path, library={})
        assert isinstance(net.blocks["feeder"], Network)
        # The sugar produces exactly one warning at the parent level.
        sugar_warnings = [
            w for w in warnings if "inline" in w.message
        ]
        assert len(sugar_warnings) == 1
        assert "feeder" in sugar_warnings[0].message


# ── Errors ────────────────────────────────────────────────────────────


class TestErrors:
    def test_unknown_role_no_path(self, tmp_path):
        _write_office_md(tmp_path, (
            "# Office: x\n\n"
            "Sources: hacker_news\n"
            "Sinks: discard\n\n"
            "Agents:\nAlex is a ghost.\n\n"
            "Connections:\n"
            "hacker_news's destination is Alex.\n"
            "Alex's brief is discard.\n"
        ))
        with pytest.raises(CompileError, match="ghost"):
            compile_office(tmp_path, library={})

    def test_unknown_source_raises(self, tmp_path):
        _write_office_md(tmp_path, (
            "# Office: x\n\n"
            "Sources: not_a_source\n"
            "Sinks: discard\n\n"
            "Agents:\nAlex is an analyst.\n\n"
            "Connections:\n"
            "not_a_source's destination is Alex.\n"
            "Alex's brief is discard.\n"
        ))
        _register_stub("stub-err", _stub_default_send_to("brief"))
        with pytest.raises(CompileError, match="unknown source"):
            compile_office(
                tmp_path,
                library={
                    "analyst": nl_role(
                        "You analyse. Send to brief.", AI="stub-err"
                    )
                },
            )

    def test_undeclared_outport_raises(self, tmp_path):
        _register_stub("stub-bad", _stub_default_send_to("brief"))
        _write_office_md(tmp_path, (
            "# Office: x\n\n"
            "Sources: hacker_news\n"
            "Sinks: discard\n\n"
            "Agents:\nAlex is an analyst.\n\n"
            "Connections:\n"
            "hacker_news's destination is Alex.\n"
            "Alex's nonexistent is discard.\n"
        ))
        with pytest.raises(CompileError, match="no outport named"):
            compile_office(
                tmp_path,
                library={
                    "analyst": nl_role(
                        "You analyse. Send to brief.", AI="stub-bad"
                    )
                },
            )


# ── Library scoping ──────────────────────────────────────────────────


class TestLibraryScoping:
    def test_top_level_library_does_not_leak_into_sub(self, tmp_path):
        """Parent's library= override applies only to the parent office.

        The sub-office must load its own roles/. We construct a
        sub-office whose library would only resolve under its own
        ``roles/``, then pass the parent a library that omits
        the sub-office's role. If the override leaked, the
        sub-office's compile would fail.
        """
        _register_stub("stub-iso", _stub_default_send_to("brief"))
        # Sub-office with its own roles analyst.py
        sub = tmp_path / "child"
        _write_office_md(sub, (
            "# Office: child\n\n"
            "Inputs: feed\n"
            "Outputs: out\n\n"
            "Agents:\nMorgan is an analyst.\n\n"
            "Connections:\n"
            "feed's destination is Morgan.\n"
            "Morgan's brief is out.\n"
        ))
        (sub / "roles").mkdir()
        (sub / "roles" / "analyst.py").write_text(
            "from dissyslab.office_v2 import nl_role\n"
            "role = nl_role('Send to brief.', AI='stub-iso')\n"
        )

        # Parent that wires the child as an OfficeRoleEntry
        _write_office_md(tmp_path, (
            "# Office: parent\n\n"
            "Sources: hacker_news\n"
            "Sinks: discard\n\n"
            "Agents:\nfeeder is an office.\n\n"
            "Connections:\n"
            "hacker_news's destination is feeder's feed.\n"
            "feeder's out is discard.\n"
        ))
        # Parent library has 'office' (sub-office) but NOT 'analyst'.
        # If the override leaked into the child, the child's compile
        # would fail looking for 'analyst'. We test by passing a
        # library that omits 'analyst'.
        net, _ = compile_office(
            tmp_path,
            library={
                "office": OfficeRoleEntry(
                    name="child", path="child"
                ),
            },
        )
        assert "feeder" in net.blocks


# ── fn_lib integration ────────────────────────────────────────────────


class TestFnLibResolution:
    """Compiler resolves ``Sasha is a deduplicator(by="url").`` to a
    Transform built from FN_LIB."""

    def test_fn_lib_role_compiles(self, tmp_path):
        _write_office_md(tmp_path, (
            "# Office: x\n\n"
            "Sources: hacker_news\n"
            "Sinks: discard\n\n"
            "Agents:\n"
            "Sasha is a deduplicator(by=\"url\").\n\n"
            "Connections:\n"
            "hacker_news's destination is Sasha.\n"
            "Sasha's out is discard.\n"
        ))
        net, warnings = compile_office(tmp_path)
        assert warnings == []
        assert "Sasha" in net.blocks
        sasha = net.blocks["Sasha"]
        from dissyslab.blocks.transform import Transform
        assert isinstance(sasha, Transform)
        # State seeded from FN_LIB.deduplicator_initial_state() — bare,
        # because ``by`` is consumed by ``fn`` (per-message), not by
        # initial_state. The framework partitions kwargs by signature.
        assert sasha.state == {"seen": set()}
        # Params passed through.
        assert sasha._params == {"by": "url"}

    def test_fn_lib_default_args_when_none_given(self, tmp_path):
        _write_office_md(tmp_path, (
            "# Office: x\n\n"
            "Sources: hacker_news\n"
            "Sinks: discard\n\n"
            "Agents:\nSasha is a deduplicator.\n\n"
            "Connections:\n"
            "hacker_news's destination is Sasha.\n"
            "Sasha's out is discard.\n"
        ))
        net, warnings = compile_office(tmp_path)
        assert warnings == []
        sasha = net.blocks["Sasha"]
        assert sasha._params == {}  # no args given
        assert sasha.state == {"seen": set()}

    def test_local_role_overrides_fn_lib(self, tmp_path):
        """An office-local roles/deduplicator.md beats the fn_lib entry."""
        _register_stub("stub-fn-override", _stub_default_send_to("out"))
        _write_office_md(tmp_path, (
            "# Office: x\n\n"
            "Sources: hacker_news\n"
            "Sinks: discard\n\n"
            "Agents:\nSasha is a deduplicator.\n\n"
            "Connections:\n"
            "hacker_news's destination is Sasha.\n"
            "Sasha's out is discard.\n"
        ))
        # Local override: an LLM-style role with the same name.
        roles_dir = tmp_path / "roles"
        roles_dir.mkdir()
        (roles_dir / "deduplicator.py").write_text(
            "from dissyslab.office_v2 import nl_role\n"
            "role = nl_role('Drop spam. Send to out.', "
            "AI='stub-fn-override')\n"
        )

        net, _ = compile_office(tmp_path)
        from dissyslab.blocks.role import Role
        # If the local role wins, Sasha is a Role (LLM-driven); if
        # fn_lib won, Sasha would be a Transform.
        assert isinstance(net.blocks["Sasha"], Role)

    def test_unknown_role_lists_both_libraries(self, tmp_path):
        _write_office_md(tmp_path, (
            "# Office: x\n\n"
            "Sources: hacker_news\n"
            "Sinks: discard\n\n"
            "Agents:\nMystery is a no_such_thing.\n\n"
            "Connections:\n"
            "hacker_news's destination is Mystery.\n"
            "Mystery's out is discard.\n"
        ))
        with pytest.raises(CompileError, match="fn_lib keys"):
            compile_office(tmp_path)

    def test_bad_kwargs_to_fn_lib_role_reports_clearly(self, tmp_path):
        """A kwarg neither callable accepts surfaces a clear CompileError."""
        _write_office_md(tmp_path, (
            "# Office: x\n\n"
            "Sources: hacker_news\n"
            "Sinks: discard\n\n"
            "Agents:\n"
            "Sasha is a deduplicator(unknown_arg=1).\n\n"
            "Connections:\n"
            "hacker_news's destination is Sasha.\n"
            "Sasha's out is discard.\n"
        ))
        with pytest.raises(CompileError, match="unknown argument"):
            compile_office(tmp_path)


# ── Gallery snapshot ──────────────────────────────────────────────────


GALLERY = Path(__file__).resolve().parents[3] / "dissyslab" / "gallery"


# Gallery offices whose sources need live credentials or optional
# packages we do not require in CI. Skipped — the compiler still
# parses them; we just cannot instantiate the source classes.
_NEEDS_LIVE_CREDS = {
    "calendar_briefing",   # GmailSource needs GMAIL_USER/GMAIL_APP_PASSWORD
    "gmail_monitor",       # same
    "org_situation_room",  # bluesky_jetstream needs websocket-client
}


def _gallery_office_dirs():
    out = []
    for d in sorted(GALLERY.iterdir()):
        if not d.is_dir():
            continue
        if d.name in _NEEDS_LIVE_CREDS:
            continue
        if (d / "office.md").exists() or (d / "network.md").exists():
            out.append(d)
    return out


class TestGalleryCompiles:
    """Every gallery office must compile to a valid runtime Network.

    We override every ``analyst``, ``editor``, ``writer``, etc. role
    with a stub-backed ``nl_role`` so no API key or LLM call is
    needed; the structural wiring is what we are testing.
    """

    def _stub_library(self, prompts: dict) -> dict:
        """Build a library that maps each role name to a stub-backed nl_role."""
        _register_stub("stub-gallery", _stub_default_send_to("brief"))
        return {
            role_name: nl_role(prompt, AI="stub-gallery")
            for role_name, prompt in prompts.items()
        }

    @pytest.mark.parametrize(
        "office_dir",
        _gallery_office_dirs(),
        ids=lambda p: p.name,
    )
    def test_compiles(self, office_dir, monkeypatch):
        # Test wiring, not the developer's shell DSL_BACKEND. If the
        # user has DSL_BACKEND=ollama (or any other backend not
        # registered in pytest), nl_role's factory would try to
        # resolve that backend at agent-instantiation time and fail.
        # Force the default backend (anthropic) for this test —
        # compile_office never actually calls the backend (we don't
        # run the network), so no API key is needed.
        monkeypatch.delenv("DSL_BACKEND", raising=False)

        net, warnings = compile_office(office_dir)
        assert isinstance(net, Network)
        # Empty or sugar-only warnings are acceptable; structural
        # warnings would be a regression worth flagging.
        for w in warnings:
            assert "inline" in w.message or "sugar" in w.message, (
                f"unexpected warning compiling {office_dir.name}: {w}"
            )


# ── CompileWarning surface ────────────────────────────────────────────


class TestCompileWarning:
    def test_str_includes_location(self):
        w = CompileWarning(message="something", location="/path")
        assert "[/path]" in str(w)
        assert "something" in str(w)

    def test_str_omits_empty_location(self):
        w = CompileWarning(message="hi")
        assert str(w) == "hi"
