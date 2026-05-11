"""Unit tests for ``office_v2.cli_helpers`` — what ``dsl build`` / ``dsl run`` do.

We do not exec the generated ``run.py`` (it would import the real
runtime and source/sink classes, possibly hitting the network). The
tests cover:

* ``cli_build`` writes ``build/run.py`` and returns 0.
* ``cli_build`` surfaces ParseError / CompileError as exit code 1
  with a friendly message on stderr.
* ``is_build_stale`` returns True when the artifact is missing,
  when an office.md is newer, or when a roles file is newer.
  Returns False once the artifact is touched after every source.
"""
from __future__ import annotations

import io
import time
from pathlib import Path

import pytest

from dissyslab.office_v2.cli_helpers import (
    _build_artifact_path,
    cli_build,
    is_build_stale,
)


# ── Helpers ───────────────────────────────────────────────────────────


def _write_office(office_dir: Path, body: str) -> None:
    office_dir.mkdir(parents=True, exist_ok=True)
    (office_dir / "office.md").write_text(body)


def _write_role(office_dir: Path, role_name: str, prompt: str) -> None:
    rl = office_dir / "roles"
    rl.mkdir(parents=True, exist_ok=True)
    (rl / f"{role_name}.md").write_text(prompt)


def _make_tiny_office(office_dir: Path) -> None:
    _write_office(office_dir, (
        "# Office: tiny\n\n"
        "Sources: hacker_news\n"
        "Sinks: discard\n\n"
        "Agents:\nAlex is an analyst.\n\n"
        "Connections:\n"
        "hacker_news's destination is Alex.\n"
        "Alex's brief is discard.\n"
    ))
    _write_role(office_dir, "analyst", "You analyse. Send to brief.")


def _bump_mtime(path: Path) -> None:
    """Touch a file so its mtime is strictly later than any prior write.

    Useful in fast-running tests where two writes within the same
    filesystem-resolution tick produce identical mtimes.
    """
    now = time.time() + 1
    path.touch()
    import os
    os.utime(path, (now, now))


# ── cli_build ─────────────────────────────────────────────────────────


class TestCliBuild:
    def test_writes_artifact(self, tmp_path):
        _make_tiny_office(tmp_path)
        out = io.StringIO()
        rc = cli_build(tmp_path, out=out)
        assert rc == 0
        assert _build_artifact_path(tmp_path).exists()

    def test_status_message_includes_path(self, tmp_path):
        _make_tiny_office(tmp_path)
        out = io.StringIO()
        cli_build(tmp_path, out=out)
        text = out.getvalue()
        assert "Wrote" in text
        assert "run.py" in text

    def test_parse_error_returns_one(self, tmp_path, capsys):
        # Missing the # Office: header → ParseError.
        (tmp_path / "office.md").write_text("Sources: rss\n")
        rc = cli_build(tmp_path)
        assert rc == 1
        captured = capsys.readouterr()
        assert "dsl build" in captured.err

    def test_compile_error_returns_one(self, tmp_path, capsys):
        # Agent uses a role not in any library and no inline path.
        _write_office(tmp_path, (
            "# Office: x\n\n"
            "Sources: hacker_news\n"
            "Sinks: discard\n\n"
            "Agents:\nAlex is a ghost.\n\n"
            "Connections:\n"
            "hacker_news's destination is Alex.\n"
            "Alex's brief is discard.\n"
        ))
        rc = cli_build(tmp_path)
        assert rc == 1
        captured = capsys.readouterr()
        assert "dsl build" in captured.err
        assert "ghost" in captured.err


# ── is_build_stale ────────────────────────────────────────────────────


class TestIsBuildStale:
    def test_missing_artifact_is_stale(self, tmp_path):
        _make_tiny_office(tmp_path)
        assert is_build_stale(tmp_path) is True

    def test_fresh_artifact_is_not_stale(self, tmp_path):
        _make_tiny_office(tmp_path)
        cli_build(tmp_path, out=io.StringIO())
        # Bump artifact mtime so it's strictly newer than every source.
        _bump_mtime(_build_artifact_path(tmp_path))
        assert is_build_stale(tmp_path) is False

    def test_office_md_change_is_stale(self, tmp_path):
        _make_tiny_office(tmp_path)
        cli_build(tmp_path, out=io.StringIO())
        _bump_mtime(_build_artifact_path(tmp_path))
        assert is_build_stale(tmp_path) is False
        # Touch office.md after the artifact.
        time.sleep(0.01)
        _bump_mtime(tmp_path / "office.md")
        assert is_build_stale(tmp_path) is True

    def test_role_file_change_is_stale(self, tmp_path):
        _make_tiny_office(tmp_path)
        cli_build(tmp_path, out=io.StringIO())
        _bump_mtime(_build_artifact_path(tmp_path))
        time.sleep(0.01)
        _bump_mtime(tmp_path / "roles" / "analyst.md")
        assert is_build_stale(tmp_path) is True

    def test_sub_office_change_is_stale(self, tmp_path):
        # Sub-office
        sub = tmp_path / "child"
        _write_office(sub, (
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
        from dissyslab.office_v2 import OfficeRoleEntry
        _write_office(tmp_path, (
            "# Office: parent\n\n"
            "Sources: hacker_news\n"
            "Sinks: discard\n\n"
            "Agents:\nfeeder is an office at child.\n\n"
            "Connections:\n"
            "hacker_news's destination is feeder's feed.\n"
            "feeder's out is discard.\n"
        ))
        cli_build(tmp_path, out=io.StringIO())
        _bump_mtime(_build_artifact_path(tmp_path))
        assert is_build_stale(tmp_path) is False
        # Edit a role file *inside the sub-office* — the parent's
        # artifact must be considered stale.
        time.sleep(0.01)
        _bump_mtime(sub / "roles" / "analyst.md")
        assert is_build_stale(tmp_path) is True
