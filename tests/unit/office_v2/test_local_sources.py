"""
Unit tests for app-local source discovery (``<office>/sources/*.py``).

Mirrors how ``roles/`` are discovered: a per-feed module exposing a
``build_source()`` callable lets one office use several distinct
sources whose block names would otherwise collide on DSL's single
generic ``rss`` component. Added alongside NetworkOfThought #190.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dissyslab.office._internals import _load_local_sources
from dissyslab.office.compiler import _build_source
from dissyslab.office.office_spec import SourceSpec


_MODULE = '''\
from dissyslab.core import Agent


class _Ticker:
    """Minimal source component with a .run generator."""
    def __init__(self, label):
        self.label = label

    def run(self):
        yield {"label": self.label}


def build_source():
    return _Ticker("__LABEL__")
'''


def _write_source(dir_: Path, name: str, label: str) -> None:
    (dir_ / "sources").mkdir(parents=True, exist_ok=True)
    (dir_ / "sources" / f"{name}.py").write_text(
        _MODULE.replace("__LABEL__", label)
    )


def test_no_sources_dir_returns_empty(tmp_path: Path):
    assert _load_local_sources(tmp_path) == {}


def test_discovers_modules_and_skips_underscored(tmp_path: Path):
    _write_source(tmp_path, "alpha", "A")
    _write_source(tmp_path, "beta", "B")
    _write_source(tmp_path, "_helper", "H")  # underscore → skipped

    found = _load_local_sources(tmp_path)
    assert set(found) == {"alpha", "beta"}
    assert callable(found["alpha"])


def test_missing_build_source_raises(tmp_path: Path):
    (tmp_path / "sources").mkdir()
    (tmp_path / "sources" / "bad.py").write_text("X = 1\n")
    with pytest.raises(ImportError):
        _load_local_sources(tmp_path)


def test_build_source_prefers_app_local_over_registry(tmp_path: Path):
    _write_source(tmp_path, "alpha", "A")
    local = _load_local_sources(tmp_path)
    src = _build_source(SourceSpec(name="alpha"), local)
    # Block name comes from the file stem.
    assert src.name == "alpha"


def test_unknown_source_without_local_still_errors(tmp_path: Path):
    from dissyslab.office._internals import CompileError

    with pytest.raises(CompileError):
        _build_source(SourceSpec(name="definitely_not_a_source"), {})
