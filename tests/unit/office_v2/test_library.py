"""Unit tests for ``office.library``.

Two layers, mirroring ``test_office_spec.py``:

1. Type-level invariants on ``AgentRoleEntry`` and ``OfficeRoleEntry``.
2. Behavioural tests for ``nl_role`` and ``load_roles_dir`` using a
   stub backend so no real LLM is contacted.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from dissyslab.backends import register_backend
from dissyslab.blocks.role import Role
from dissyslab.office.library import (
    AgentRoleEntry,
    OfficeRoleEntry,
    RoleEntry,
    Library,
    DEFAULT_AI,
    _extract_send_to_ports,
    load_roles_dir,
    nl_role,
    specialist_role,
)


# ── A tiny stub backend the tests can drive deterministically ──────────


class _StubBackend:
    """Backend whose ``complete`` returns a fixed reply (or one from a queue).

    Tests register an instance under a unique name with
    ``register_backend`` and pass that name to ``nl_role(AI=...)``.
    """

    def __init__(self, reply):
        # ``reply`` may be a single string (returned every call) or a
        # callable taking the user prompt and returning a string.
        self.reply = reply
        self.calls = []

    def complete(self, *, system, user, max_tokens=1024,
                 temperature=1.0, model=None) -> str:
        self.calls.append({"system": system, "user": user})
        if callable(self.reply):
            return self.reply(user)
        return self.reply


def _register_stub(name: str, reply) -> _StubBackend:
    stub = _StubBackend(reply)
    register_backend(name, lambda: stub)
    return stub


# ── AgentRoleEntry validation ──────────────────────────────────────────


class TestAgentRoleEntry:
    def test_minimal(self):
        entry = AgentRoleEntry(
            name="analyst",
            in_ports=("in_",),
            out_ports=("brief",),
            factory=lambda: object(),
        )
        assert entry.name == "analyst"
        assert entry.in_ports == ("in_",)
        assert entry.out_ports == ("brief",)
        assert entry.description == ""

    def test_empty_name_allowed(self):
        # Empty name is allowed because nl_role returns nameless
        # entries and load_roles_dir fills them in.
        entry = AgentRoleEntry(
            name="",
            in_ports=("in_",),
            out_ports=("a",),
            factory=lambda: object(),
        )
        assert entry.name == ""

    def test_ports_coerced_to_tuple(self):
        entry = AgentRoleEntry(
            name="x",
            in_ports=["in_"],
            out_ports=["a", "b"],
            factory=lambda: object(),
        )
        assert isinstance(entry.in_ports, tuple)
        assert isinstance(entry.out_ports, tuple)

    def test_callable(self):
        sentinel = object()
        entry = AgentRoleEntry(
            name="x",
            in_ports=("in_",),
            out_ports=("a",),
            factory=lambda: sentinel,
        )
        assert entry() is sentinel

    def test_duplicate_out_ports_rejected(self):
        with pytest.raises(ValueError, match="duplicate"):
            AgentRoleEntry(
                name="x",
                in_ports=("in_",),
                out_ports=("a", "a"),
                factory=lambda: None,
            )

    def test_no_ports_at_all_rejected(self):
        with pytest.raises(ValueError, match="no ports"):
            AgentRoleEntry(
                name="x",
                in_ports=(),
                out_ports=(),
                factory=lambda: None,
            )

    def test_non_callable_factory_rejected(self):
        with pytest.raises(TypeError, match="callable"):
            AgentRoleEntry(
                name="x",
                in_ports=("in_",),
                out_ports=("a",),
                factory="not a function",  # type: ignore[arg-type]
            )

    def test_empty_port_string_rejected(self):
        with pytest.raises(ValueError, match="non-empty"):
            AgentRoleEntry(
                name="x",
                in_ports=("",),
                out_ports=("a",),
                factory=lambda: None,
            )


# ── OfficeRoleEntry validation ─────────────────────────────────────────


class TestOfficeRoleEntry:
    def test_minimal(self):
        entry = OfficeRoleEntry(name="news_monitor", path="../news_monitor")
        assert entry.name == "news_monitor"
        assert entry.path == "../news_monitor"
        assert entry.description == ""

    def test_empty_path_rejected(self):
        with pytest.raises(ValueError, match="empty path"):
            OfficeRoleEntry(name="x", path="")


# ── _extract_send_to_ports — moved from parser.py in Step 4 ────────────


class TestExtractSendToPorts:
    def test_simple(self):
        assert _extract_send_to_ports("Always send to briefing.") == (
            "briefing",
        )

    def test_two_lines(self):
        text = "If X, send to keep.\nOtherwise send to discard."
        assert _extract_send_to_ports(text) == ("keep", "discard")

    def test_or_to_form(self):
        text = "Send to keep or to discard."
        assert _extract_send_to_ports(text) == ("keep", "discard")

    def test_dedup_in_order(self):
        text = "Send to A.\nLater send to A or to B."
        assert _extract_send_to_ports(text) == ("A", "B")

    def test_no_send_returns_empty(self):
        text = "You are an analyst. Read carefully."
        assert _extract_send_to_ports(text) == ()

    def test_ignores_intro_about_sending(self):
        # "responds by sending zero or more messages" should NOT
        # contribute ports, because the line has no "send to".
        text = (
            "You respond by sending zero or more messages, each "
            "addressed to a destination role."
        )
        assert _extract_send_to_ports(text) == ()


# ── nl_role port extraction ────────────────────────────────────────────


class TestNLRolePortExtraction:
    def test_single_port(self):
        entry = nl_role("You are a reporter. Always send to briefing.")
        assert entry.out_ports == ("briefing",)
        assert entry.in_ports == ("in_",)

    def test_multiple_ports(self):
        entry = nl_role("Triage incoming articles. Send to keep or to discard.")
        assert entry.out_ports == ("keep", "discard")

    def test_no_send_to_raises(self):
        with pytest.raises(ValueError, match="no output ports"):
            nl_role("You are a reporter.")

    def test_empty_prompt_raises(self):
        with pytest.raises(ValueError, match="non-empty"):
            nl_role("")

    def test_returns_agent_role_entry(self):
        entry = nl_role("Send to summary.")
        assert isinstance(entry, AgentRoleEntry)
        # The factory should not have been invoked yet (lazy backend).
        # No ANTHROPIC_API_KEY is required to construct the entry.


# ── nl_role agent behaviour with a stub backend ────────────────────────


class TestNLRoleAgentBehaviour:
    def test_factory_returns_role_agent(self):
        _register_stub("stub-trivial", json.dumps(
            {"send_to": "out", "text": "ok"}))
        entry = nl_role("Send to out.", AI="stub-trivial")
        agent = entry()
        assert isinstance(agent, Role)
        assert agent.statuses == ["out"]

    def test_routes_to_send_to(self):
        _register_stub(
            "stub-keep",
            json.dumps({"send_to": "keep", "text": "interesting"}),
        )
        entry = nl_role(
            "Triage emails. Send to keep or to discard.",
            AI="stub-keep",
        )
        agent = entry()
        # Drive role_fn directly to avoid threads/queues. role_fn is
        # stored as agent._fn by the Role superclass.
        results = agent._fn({"body": "hi"})
        assert len(results) == 1
        msg, status = results[0]
        assert status == "keep"
        assert msg["send_to"] == "keep"
        assert msg["body"] == "hi"  # upstream metadata preserved

    def test_default_destination_when_send_to_missing(self):
        _register_stub("stub-no-key", json.dumps({"text": "no key here"}))
        entry = nl_role("Send to first or to second.", AI="stub-no-key")
        agent = entry()
        results = agent._fn({"x": 1})
        assert len(results) == 1
        _msg, status = results[0]
        assert status == "first"  # first declared port = default

    def test_routes_to_list_of_destinations(self):
        _register_stub(
            "stub-list",
            json.dumps({"send_to": ["first", "second"], "text": "fan out"}),
        )
        entry = nl_role("Send to first or to second.", AI="stub-list")
        agent = entry()
        results = agent._fn({"k": 1})
        statuses = [s for _m, s in results]
        assert statuses == ["first", "second"]

    def test_plain_text_reply_routes_to_default(self):
        _register_stub("stub-text", "Just plain text")
        entry = nl_role("Always send to summary.", AI="stub-text")
        agent = entry()
        results = agent._fn({"k": 1})
        assert len(results) == 1
        msg, status = results[0]
        assert status == "summary"
        assert msg == "Just plain text"

    def test_exception_in_backend_returns_empty_list(self):
        def boom(_user):
            raise RuntimeError("boom")

        _register_stub("stub-boom", boom)
        entry = nl_role("Send to anywhere.", AI="stub-boom")
        agent = entry()
        # Should swallow the error and return [] so the network does
        # not crash on a single bad LLM call.
        assert agent._fn({"k": 1}) == []

    def test_string_input_is_serialised(self):
        captured = {}

        def reply(user):
            captured["user"] = user
            return json.dumps({"send_to": "out", "text": "ok"})

        _register_stub("stub-str", reply)
        entry = nl_role("Send to out.", AI="stub-str")
        agent = entry()
        agent._fn("hello")
        assert captured["user"] == "hello"


class TestSpecialistRole:
    """specialist_role wraps a deterministic text -> dict transform
    into the same AgentRoleEntry shape that nl_role produces. Tests
    here mirror TestNLRoleAgentBehaviour but with a plain Python
    transform instead of a stub LLM backend."""

    def test_factory_returns_role_agent(self):
        entry = specialist_role(lambda text: {"k": len(text)})
        agent = entry()
        assert isinstance(agent, Role)
        assert agent.statuses == ["out_"]
        assert entry.in_ports == ("in_",)
        assert entry.out_ports == ("out_",)

    def test_merges_annotation_into_upstream_dict(self):
        def transform(text):
            return {"length": len(text), "upper": text.upper()}

        entry = specialist_role(transform)
        agent = entry()
        results = agent._fn({"text": "hi", "url": "http://x"})
        assert len(results) == 1
        msg, status = results[0]
        assert status == "out_"
        # Upstream fields preserved
        assert msg["url"] == "http://x"
        # Annotation merged
        assert msg["length"] == 2
        assert msg["upper"] == "HI"

    def test_reads_configurable_input_field(self):
        captured = {}

        def transform(text):
            captured["text"] = text
            return {"ok": True}

        entry = specialist_role(transform, input_field="title")
        agent = entry()
        agent._fn({"title": "the title", "text": "the body"})
        assert captured["text"] == "the title"

    def test_non_dict_upstream_message_stringified(self):
        captured = {}

        def transform(text):
            captured["text"] = text
            return {"len": len(text)}

        entry = specialist_role(transform)
        agent = entry()
        results = agent._fn(42)
        assert captured["text"] == "42"
        # Non-dict upstream messages don't merge; the annotation dict
        # is returned directly.
        msg, _status = results[0]
        assert msg == {"len": 2}

    def test_empty_text_skips_transform(self):
        # specialist_role should not invoke the transform on an empty
        # text payload. Useful for fields that are sometimes missing.
        called = []

        def transform(text):
            called.append(text)
            return {"ok": True}

        entry = specialist_role(transform)
        agent = entry()
        results = agent._fn({"text": ""})
        # Message passes through unchanged on out_ port
        assert results == [({"text": ""}, "out_")]
        assert called == []

    def test_exception_in_transform_returns_empty_list(self):
        def boom(_text):
            raise RuntimeError("boom")

        entry = specialist_role(boom)
        agent = entry()
        # Match nl_role's behavior: log and drop the message so a
        # single bad call doesn't crash the network.
        assert agent._fn({"text": "anything"}) == []

    def test_non_dict_return_routed_directly(self):
        # If the transform returns a non-dict (e.g. a plain string),
        # it goes downstream as the whole payload, mirroring nl_role's
        # plain-text-reply path.
        entry = specialist_role(lambda text: text.upper())
        agent = entry()
        results = agent._fn({"text": "hello"})
        msg, status = results[0]
        assert msg == "HELLO"
        assert status == "out_"

    def test_custom_out_port(self):
        entry = specialist_role(
            lambda text: {"k": text},
            out_port="annotated",
        )
        assert entry.out_ports == ("annotated",)
        agent = entry()
        assert agent.statuses == ["annotated"]
        results = agent._fn({"text": "x"})
        _msg, status = results[0]
        assert status == "annotated"

    def test_non_callable_transform_rejected(self):
        with pytest.raises(TypeError, match="callable"):
            specialist_role("not a function")  # type: ignore[arg-type]


class TestNLRoleAIAlias:
    def test_default_ai_constant(self):
        # DEFAULT_AI is the constant that documents the canonical
        # human-readable name for the default backend.
        assert DEFAULT_AI.lower() == "claude"

    def test_default_ai_does_not_eagerly_resolve(self):
        # Constructing an entry with no AI argument should not require
        # any API key — the backend is resolved lazily inside the
        # factory, not at nl_role call time.
        entry = nl_role("Send to out.")
        assert isinstance(entry, AgentRoleEntry)
        # The factory has not been called yet — backend not resolved.

    def test_default_ai_honors_dsl_backend_env_var(self, monkeypatch):
        """Roles built without an explicit AI follow DSL_BACKEND at run time.

        This is what makes ``DSL_BACKEND=ollama`` actually flip every
        gallery role to ollama — gallery .md files are loaded with no
        AI argument, so each role's backend choice is deferred until
        the agent runs.
        """
        stub = _register_stub(
            "stub-runtime-default",
            json.dumps({"send_to": "out", "text": "ok"}),
        )
        monkeypatch.setenv("DSL_BACKEND", "stub-runtime-default")
        entry = nl_role("Send to out.")  # no AI → defer to runtime
        agent = entry()
        agent._fn({"x": 1})
        assert stub.calls, (
            "expected DSL_BACKEND to route the call to the stub backend"
        )

    def test_explicit_ai_overrides_dsl_backend(self, monkeypatch):
        """An explicit AI argument locks that backend in regardless of DSL_BACKEND."""
        explicit_stub = _register_stub(
            "stub-explicit",
            json.dumps({"send_to": "out", "text": "ok"}),
        )
        ignored_stub = _register_stub(
            "stub-ignored",
            json.dumps({"send_to": "out", "text": "should not be called"}),
        )
        monkeypatch.setenv("DSL_BACKEND", "stub-ignored")
        entry = nl_role("Send to out.", AI="stub-explicit")
        agent = entry()
        agent._fn({"x": 1})
        assert explicit_stub.calls, (
            "expected the explicit AI argument to win over DSL_BACKEND"
        )
        assert not ignored_stub.calls, (
            "DSL_BACKEND should be ignored when AI is given explicitly"
        )
        # We do NOT call entry() because that would try anthropic.


# ── load_roles_dir ─────────────────────────────────────────────────────


class TestLoadRolesDir:
    def test_missing_dir_returns_empty_mapping(self, tmp_path):
        out = load_roles_dir(tmp_path / "does_not_exist")
        assert out == {}

    def test_empty_dir_returns_empty_mapping(self, tmp_path):
        assert load_roles_dir(tmp_path) == {}

    def test_loads_md_files(self, tmp_path):
        (tmp_path / "analyst.md").write_text(
            "You are an analyst. Send to brief.\n"
        )
        (tmp_path / "editor.md").write_text(
            "You edit. Send to publish or to revise.\n"
        )
        out = load_roles_dir(tmp_path)
        assert set(out) == {"analyst", "editor"}

        analyst = out["analyst"]
        assert isinstance(analyst, AgentRoleEntry)
        assert analyst.name == "analyst"
        assert analyst.out_ports == ("brief",)

        editor = out["editor"]
        assert editor.out_ports == ("publish", "revise")

    def test_underscore_md_skipped(self, tmp_path):
        (tmp_path / "_template.md").write_text("Send to anywhere.")
        assert load_roles_dir(tmp_path) == {}

    def test_loads_py_files(self, tmp_path):
        (tmp_path / "rss.py").write_text(
            "from dissyslab.office.library import OfficeRoleEntry\n"
            "role = OfficeRoleEntry(name='', path='./somewhere')\n"
        )
        out = load_roles_dir(tmp_path)
        assert set(out) == {"rss"}
        rss = out["rss"]
        assert isinstance(rss, OfficeRoleEntry)
        assert rss.name == "rss"  # filled in from the filename

    def test_py_keeps_explicit_name(self, tmp_path):
        (tmp_path / "x.py").write_text(
            "from dissyslab.office.library import OfficeRoleEntry\n"
            "role = OfficeRoleEntry(name='custom', path='./p')\n"
        )
        out = load_roles_dir(tmp_path)
        # The dict key follows the filename; the entry's own .name
        # field is whatever the module set.
        assert out["x"].name == "custom"

    def test_py_missing_role_attribute(self, tmp_path):
        (tmp_path / "broken.py").write_text("x = 1\n")
        with pytest.raises(ValueError, match="no top-level 'role'"):
            load_roles_dir(tmp_path)

    def test_py_wrong_type_rejected(self, tmp_path):
        (tmp_path / "wrong.py").write_text("role = 42\n")
        with pytest.raises(TypeError, match="AgentRoleEntry or OfficeRoleEntry"):
            load_roles_dir(tmp_path)

    def test_underscore_py_skipped(self, tmp_path):
        (tmp_path / "__init__.py").write_text("")
        assert load_roles_dir(tmp_path) == {}

    def test_duplicate_stem_md_md(self, tmp_path):
        # Two .md files with the same stem can't co-exist; let's
        # simulate via .md and .py with the same stem.
        (tmp_path / "x.md").write_text("Send to out.")
        (tmp_path / "x.py").write_text(
            "from dissyslab.office.library import OfficeRoleEntry\n"
            "role = OfficeRoleEntry(name='x', path='./p')\n"
        )
        with pytest.raises(ValueError, match="duplicate"):
            load_roles_dir(tmp_path)


# ── Type aliases reachable & idiomatic ─────────────────────────────────


class TestTypeAliases:
    def test_role_entry_union_accepts_both(self):
        # Static type-checker concerns aside, both kinds satisfy the
        # runtime structural requirement: they are dataclasses with
        # name + description.
        a: RoleEntry = AgentRoleEntry(
            name="x",
            in_ports=("in_",),
            out_ports=("a",),
            factory=lambda: None,
        )
        b: RoleEntry = OfficeRoleEntry(name="y", path="./p")
        for entry in (a, b):
            assert hasattr(entry, "name")
            assert hasattr(entry, "description")

    def test_library_dict_works(self):
        lib: Library = {
            "x": OfficeRoleEntry(name="x", path="./p"),
        }
        assert lib["x"].path == "./p"


# ── Named contracts (α) ───────────────────────────────────────────────


class TestNamedContracts:
    """Cover the two named output contracts: passthrough, structured.
    The point of the named-contract design is that a role can opt out
    of the historical {send_to, text} envelope when its prompt needs
    a specific JSON top-level key (e.g. debate panellists that emit
    ``{"qwen": {answer, reasoning, confidence}}``).
    """

    def _capture_system_prompt(self, contract: str) -> str:
        """Build a role with the given contract and return the system
        prompt the backend actually sees on a complete() call."""
        stub = _register_stub(
            f"stub-contract-{contract}", '{"send_to": "out", "text": "ok"}'
        )
        entry = nl_role(
            "You answer. Send to out.",
            AI=f"stub-contract-{contract}",
            contract=contract,
        )
        agent = entry()
        # Drive one role_fn call so the backend is exercised.
        agent._fn({"problem": "x"})
        return stub.calls[0]["system"]

    def test_passthrough_appends_send_to_text_template(self):
        """The default contract should still produce the historical
        {send_to, text} template — every gallery app shipped before
        the α change relies on this and must keep working."""
        system = self._capture_system_prompt("passthrough")
        assert "send_to" in system
        assert '"text"' in system
        assert "<content>" in system

    def test_structured_appends_no_contract(self):
        """The structured contract appends nothing. The role's own .md
        is fully responsible for the output JSON shape."""
        system = self._capture_system_prompt("structured")
        # No {send_to, text} template appended.
        assert "<content>" not in system
        # The user's prompt body is still there.
        assert "Send to out." in system

    def test_unknown_contract_raises(self):
        with pytest.raises(ValueError) as exc:
            nl_role("Send to out.", contract="bogus")
        assert "bogus" in str(exc.value)
        # Error names the legal values.
        assert "passthrough" in str(exc.value)
        assert "structured" in str(exc.value)

    def test_default_contract_is_passthrough(self):
        """Backward compat: nl_role with no contract kwarg must behave
        identically to nl_role(contract='passthrough')."""
        a = self._capture_system_prompt("passthrough")
        # Build a default entry the same way.
        stub = _register_stub(
            "stub-contract-default", '{"send_to": "out", "text": "ok"}'
        )
        entry = nl_role(
            "You answer. Send to out.", AI="stub-contract-default",
        )
        agent = entry()
        agent._fn({"problem": "x"})
        b = stub.calls[0]["system"]
        assert a == b


class TestRoleFrontMatter:
    """The .md role file can carry a YAML ``--- ... ---`` block on top
    that names ``contract:`` and ``AI:``. ``load_roles_dir`` parses it
    and threads the values through to ``nl_role``.
    """

    def test_structured_contract_via_front_matter(self, tmp_path):
        stub = _register_stub(
            "stub-fm-structured", '{"out": {"value": 1}}'
        )
        roles = tmp_path / "roles"
        roles.mkdir()
        (roles / "agent.md").write_text(
            "---\n"
            "contract: structured\n"
            f"AI: stub-fm-structured\n"
            "---\n"
            "# Role: agent\n\n"
            "You answer. Send to out.\n"
        )
        lib = load_roles_dir(roles)
        entry = lib["agent"]
        agent = entry()
        agent._fn({"problem": "x"})
        system = stub.calls[0]["system"]
        # No {send_to, text} template appended.
        assert "<content>" not in system
        # User's prompt body is preserved.
        assert "Send to out." in system

    def test_no_front_matter_keeps_default_passthrough(self, tmp_path):
        stub = _register_stub(
            "stub-fm-none", '{"send_to": "out", "text": "ok"}'
        )
        roles = tmp_path / "roles"
        roles.mkdir()
        (roles / "agent.md").write_text(
            "# Role: agent\n\n"
            "You answer. Send to out.\n"
        )
        lib = load_roles_dir(roles)
        # No explicit AI in this file; tell the factory directly.
        agent = lib["agent"](AI="stub-fm-none")
        agent._fn({"problem": "x"})
        system = stub.calls[0]["system"]
        # Default = passthrough = {send_to, text} template appended.
        assert "<content>" in system

    def test_unknown_front_matter_keys_ignored(self, tmp_path):
        """Forward compatibility: future framework versions might use
        the same front-matter block for additional keys. Unknown keys
        must NOT break the loader."""
        stub = _register_stub(
            "stub-fm-unknown", '{"out": {"v": 1}}'
        )
        roles = tmp_path / "roles"
        roles.mkdir()
        (roles / "agent.md").write_text(
            "---\n"
            "contract: structured\n"
            f"AI: stub-fm-unknown\n"
            "future_feature: some_value\n"
            "---\n"
            "# Role: agent\n\n"
            "You answer. Send to out.\n"
        )
        lib = load_roles_dir(roles)
        assert "agent" in lib  # didn't raise

    def test_unclosed_front_matter_leaves_file_unchanged(self, tmp_path):
        """If the closing ``---`` is missing, treat the whole file as
        prompt body. The role will fail at nl_role parse time if the
        body doesn't declare any outports, but the loader itself
        doesn't crash."""
        stub = _register_stub(
            "stub-fm-unclosed", '{"send_to": "out", "text": "ok"}'
        )
        roles = tmp_path / "roles"
        roles.mkdir()
        (roles / "agent.md").write_text(
            "---\n"
            "contract: structured\n"
            "# Role: agent\n\n"
            "You answer. Send to out.\n"
        )
        # Should still load; the would-be front matter is treated as
        # part of the prompt body.
        lib = load_roles_dir(roles)
        assert "agent" in lib

    def test_front_matter_bad_line_shape_raises(self, tmp_path):
        """A front matter line with no colon is a typo we should
        surface at load time, not silently skip."""
        roles = tmp_path / "roles"
        roles.mkdir()
        (roles / "agent.md").write_text(
            "---\n"
            "contract structured\n"  # missing colon
            "---\n"
            "# Role: agent\n\n"
            "Send to out.\n"
        )
        with pytest.raises((ValueError,)):
            load_roles_dir(roles)
