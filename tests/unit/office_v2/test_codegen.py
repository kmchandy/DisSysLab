"""Unit tests for ``office_v2.codegen``.

Codegen emits a ``run.py`` whose execution produces the same Network
that ``compile_office`` would build directly. These tests assert on
the *source text* the renderer produces — the generated file is the
artifact students read, so its shape matters.

We do not exec the generated file (it would import real source
classes that may need credentials or live network access). Instead
we:

* assert on the structural pieces — imports, library loads, builder
  functions, ``__main__`` block, connection-comment annotations;
* compile the rendered text to bytecode with ``compile()`` so that
  any syntactic regression in the emitter fails loud.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from dissyslab.office_v2 import nl_role, OfficeRoleEntry
from dissyslab.office_v2.codegen import emit_run_py, render_run_py


# ── Helpers ───────────────────────────────────────────────────────────


def _write(office_dir: Path, body: str) -> None:
    office_dir.mkdir(parents=True, exist_ok=True)
    (office_dir / "office.md").write_text(body)


def _write_role(office_dir: Path, role_name: str, prompt: str) -> None:
    rl = office_dir / "roles"
    rl.mkdir(parents=True, exist_ok=True)
    (rl / f"{role_name}.md").write_text(prompt)


# ── Closed-office happy path ──────────────────────────────────────────


class TestClosedOffice:
    def _make(self, tmp_path: Path) -> Path:
        _write(tmp_path, (
            "# Office: tiny\n\n"
            "Sources: hacker_news\n"
            "Sinks: discard\n\n"
            "Agents:\nAlex is an analyst.\n\n"
            "Connections:\n"
            "hacker_news's destination is Alex.\n"
            "Alex's brief is discard.\n"
        ))
        _write_role(tmp_path, "analyst", "You analyse. Send to brief.")
        return tmp_path

    def test_compiles_to_valid_python(self, tmp_path):
        office_dir = self._make(tmp_path)
        text = render_run_py(office_dir)
        # Any syntax error here fails the test with a clear traceback.
        compile(text, "<generated>", "exec")

    def test_has_main_block(self, tmp_path):
        office_dir = self._make(tmp_path)
        text = render_run_py(office_dir)
        assert 'if __name__ == "__main__":' in text
        assert "build_tiny().run_network()" in text

    def test_has_builder_function(self, tmp_path):
        office_dir = self._make(tmp_path)
        text = render_run_py(office_dir)
        assert "def build_tiny() -> Network:" in text

    def test_imports_collated(self, tmp_path):
        office_dir = self._make(tmp_path)
        text = render_run_py(office_dir)
        assert "from dissyslab.network import Network" in text
        assert "from dissyslab.blocks.source import Source" in text
        assert "from dissyslab.blocks.sink import Sink" in text
        assert "rss_normalizer" in text  # hacker_news is RSS-typed
        assert "from dissyslab.components.sinks.discard import Discard" in text

    def test_library_loaded_relative_to_run_py(self, tmp_path):
        office_dir = self._make(tmp_path)
        text = render_run_py(office_dir)
        # build/run.py lives one level below the office; ``..`` is
        # the office dir.
        assert "_HERE = Path(__file__).resolve().parent" in text
        assert "_load_lib(_HERE / '..')" in text

    def test_writes_to_build_dir(self, tmp_path):
        office_dir = self._make(tmp_path)
        out = emit_run_py(office_dir)
        assert out == office_dir / "build" / "run.py"
        assert out.exists()
        assert (office_dir / "build" / "__init__.py").exists()
        # The text on disk equals what render_run_py returned.
        assert out.read_text() == render_run_py(office_dir)


# ── Connection comments ───────────────────────────────────────────────


class TestConnectionComments:
    def test_leaf_to_leaf_comment(self, tmp_path):
        _write(tmp_path, (
            "# Office: c\n\n"
            "Sources: hacker_news\n"
            "Sinks: discard\n\n"
            "Agents:\nAlex is an analyst.\n\n"
            "Connections:\n"
            "hacker_news's destination is Alex.\n"
            "Alex's brief is discard.\n"
        ))
        _write_role(tmp_path, "analyst", "You analyse. Send to brief.")
        text = render_run_py(tmp_path)
        # Source's "destination" port translates to "out_" with a
        # comment showing the original wording.
        assert (
            "('hacker_news', 'out_', 'Alex', 'in_'),    "
            "# hacker_news's destination → Alex"
        ) in text
        # Role's "brief" semantic port translates to "out_" (single
        # outport convention) with the original semantic name
        # preserved in the comment.
        assert (
            "('Alex', 'out_', 'discard', 'in_'),    "
            "# Alex's brief → discard"
        ) in text

    def test_external_in_comment(self, tmp_path):
        _write(tmp_path, (
            "# Office: o\n\n"
            "Inputs: feed\n"
            "Outputs: report\n\n"
            "Agents:\nAlex is an analyst.\n\n"
            "Connections:\n"
            "feed's destination is Alex.\n"
            "Alex's brief is report.\n"
        ))
        _write_role(tmp_path, "analyst", "Send to brief.")
        text = render_run_py(tmp_path)
        assert "external 'feed' → Alex" in text
        assert "Alex's brief → external 'report'" in text


# ── Open office (no __main__ block) ───────────────────────────────────


class TestOpenOffice:
    def test_no_main_block(self, tmp_path):
        _write(tmp_path, (
            "# Office: o\n\n"
            "Inputs: feed\n"
            "Outputs: report\n\n"
            "Agents:\nAlex is an analyst.\n\n"
            "Connections:\n"
            "feed's destination is Alex.\n"
            "Alex's brief is report.\n"
        ))
        _write_role(tmp_path, "analyst", "Send to brief.")
        text = render_run_py(tmp_path)
        assert 'if __name__ == "__main__":' not in text
        assert "inports=['feed']" in text
        assert "outports=['report']" in text


# ── Sub-office recursion ──────────────────────────────────────────────


class TestSubOffices:
    def _build_pair(self, root: Path) -> Path:
        # Sub-office
        sub = root / "child"
        _write(sub, (
            "# Office: child\n\n"
            "Inputs: feed\n"
            "Outputs: out\n\n"
            "Agents:\nMorgan is an analyst.\n\n"
            "Connections:\n"
            "feed's destination is Morgan.\n"
            "Morgan's brief is out.\n"
        ))
        _write_role(sub, "analyst", "Send to brief.")

        # Parent
        _write(root, (
            "# Office: parent\n\n"
            "Sources: hacker_news\n"
            "Sinks: discard\n\n"
            "Agents:\nfeeder is an office.\n\n"
            "Connections:\n"
            "hacker_news's destination is feeder's feed.\n"
            "feeder's out is discard.\n"
        ))
        return root

    def test_child_emitted_before_parent(self, tmp_path):
        root = self._build_pair(tmp_path)
        text = render_run_py(
            root,
            library={"office": OfficeRoleEntry(name="child", path="child")},
        )
        # Both builder functions exist.
        assert "def build_child() -> Network:" in text
        assert "def build_parent() -> Network:" in text
        # And the child appears textually before the parent.
        assert text.index("def build_child()") < text.index("def build_parent()")

    def test_parent_uses_build_child_call(self, tmp_path):
        root = self._build_pair(tmp_path)
        text = render_run_py(
            root,
            library={"office": OfficeRoleEntry(name="child", path="child")},
        )
        # The parent's blocks dict materialises the sub-office via a
        # function call, not via roles[...].
        assert '"feeder": build_child(),' in text

    def test_each_office_loads_its_own_library(self, tmp_path):
        root = self._build_pair(tmp_path)
        text = render_run_py(
            root,
            library={"office": OfficeRoleEntry(name="child", path="child")},
        )
        # One _ROLES_<office> per office.
        assert "_ROLES_PARENT = _load_lib(_HERE / '..')" in text
        assert "_ROLES_CHILD" in text and "_load_lib(_HERE / '../child')" in text


# ── fn_lib agents render as readable Transform construction ──────────


class TestFnLibAgents:
    """``Sasha is a deduplicator(by="url").`` should produce a tidy
    ``Transform(fn=..., params=..., state=..., name=...)`` line in
    the generated artifact, not a roles_lib factory call."""

    def test_emitted_text_contains_transform_construction(self, tmp_path):
        _write(tmp_path, (
            "# Office: dedup_demo\n\n"
            "Sources: hacker_news\n"
            "Sinks: discard\n\n"
            "Agents:\nSasha is a deduplicator(by=\"url\").\n\n"
            "Connections:\n"
            "hacker_news's destination is Sasha.\n"
            "Sasha's out is discard.\n"
        ))
        text = render_run_py(tmp_path)

        # The fn_lib import is present.
        assert "from dissyslab.fn_lib import FN_LIB" in text
        assert "from dissyslab.blocks.transform import Transform" in text

        # Sasha is built as a Transform with all four kwargs.
        # ``by`` is consumed only by ``fn`` (deduplicator's
        # initial_state takes no args), so it appears once — in
        # ``params=`` — and ``initial_state()`` is called bare.
        assert "\"Sasha\": Transform(" in text
        assert "fn=FN_LIB['deduplicator'].fn" in text
        assert "params={'by': 'url'}" in text
        assert "state=FN_LIB['deduplicator'].initial_state()" in text
        assert "name='Sasha'" in text
        # The duplication we explicitly fixed: ``by`` should NOT
        # appear inside the initial_state(...) call.
        assert "initial_state(by='url')" not in text

    def test_emitted_text_compiles_to_bytecode(self, tmp_path):
        _write(tmp_path, (
            "# Office: dedup_demo\n\n"
            "Sources: hacker_news\n"
            "Sinks: discard\n\n"
            "Agents:\nSasha is a deduplicator.\n\n"
            "Connections:\n"
            "hacker_news's destination is Sasha.\n"
            "Sasha's out is discard.\n"
        ))
        text = render_run_py(tmp_path)
        # If our renderer emits invalid Python, this raises SyntaxError.
        compile(text, "<generated>", "exec")

    def test_no_args_emits_no_kwargs_call(self, tmp_path):
        _write(tmp_path, (
            "# Office: dedup_demo\n\n"
            "Sources: hacker_news\n"
            "Sinks: discard\n\n"
            "Agents:\nSasha is a deduplicator.\n\n"
            "Connections:\n"
            "hacker_news's destination is Sasha.\n"
            "Sasha's out is discard.\n"
        ))
        text = render_run_py(tmp_path)
        # No-args case: empty params dict, bare initial_state() call.
        assert "params={}" in text
        assert "FN_LIB['deduplicator'].initial_state()" in text


# ── Render is deterministic ───────────────────────────────────────────


class TestDeterminism:
    def test_same_office_renders_same_text(self, tmp_path):
        _write(tmp_path, (
            "# Office: t\n\n"
            "Sources: hacker_news\n"
            "Sinks: discard\n\n"
            "Agents:\nAlex is an analyst.\n\n"
            "Connections:\n"
            "hacker_news's destination is Alex.\n"
            "Alex's brief is discard.\n"
        ))
        _write_role(tmp_path, "analyst", "Send to brief.")
        a = render_run_py(tmp_path)
        b = render_run_py(tmp_path)
        assert a == b
