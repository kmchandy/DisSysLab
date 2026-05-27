"""
CLI helpers — what `dsl build` and `dsl run` actually do.

Two thin handlers wrap the office pipeline so the top-level
argparse code in ``dissyslab.cli`` stays small and readable.

* ``cli_build(office_dir)`` — parse, validate wiring, codegen
  ``build/run.py``. Prints the artifact path on success and any
  ``CompileWarning``s the compiler surfaced. Compile-time errors
  (missing role, sink as sender, etc.) are turned into friendly
  messages.

* ``cli_run(office_dir)`` — if ``build/run.py`` is missing or any
  source file under the office tree is newer than the artifact,
  rebuild. Then execute the artifact via ``runpy.run_path`` so the
  network starts under the same ``__main__`` entry point a student
  would use with ``python build/run.py`` directly.

Mtime-based staleness
=====================

We walk the office tree (parent + sub-offices, even when sub-offices
live outside the parent's directory) and compare each ``.md`` /
``.py`` source file's mtime to ``build/run.py``'s. Any newer source
file triggers a rebuild. We ignore ``__pycache__`` and the
``build/`` directory itself so a fresh artifact does not appear
"older than itself".

This is deliberately simple — no content hashing, no cache
subsystem. mtime is the obvious thing students can reason about:
"I edited office.md, so dsl run rebuilds."
"""
from __future__ import annotations

import runpy
import sys
from pathlib import Path
from typing import Iterable, Iterator, List, Optional

from dissyslab.office.codegen import (
    _build_tree,
    _topo_order,
    emit_run_py,
)
from dissyslab.office.compiler import CompileError, CompileWarning
from dissyslab.office.parser_errors import ParseError


# ── Build-tree mtime walk ─────────────────────────────────────────────


def _office_tree_files(office_dir: Path) -> Iterator[Path]:
    """Yield every source file that contributes to compiling an office tree.

    For each office in the dependency tree (parent + sub-offices,
    deduplicated), yield:

    * its ``office.md`` (or legacy ``network.md``);
    * every ``*.md`` and ``*.py`` in ``roles/``.

    Files starting with ``_`` (e.g. ``__init__.py``) are skipped —
    ``load_roles_dir`` skips them too.
    """
    root = _build_tree(Path(office_dir).resolve())
    for node in _topo_order(root):
        md = node.office_dir / "office.md"
        if not md.exists():
            md = node.office_dir / "network.md"
        if md.exists():
            yield md
        d = node.office_dir / "roles"
        if not d.is_dir():
            continue
        for f in sorted(d.iterdir()):
            if not f.is_file():
                continue
            if f.name.startswith("_"):
                continue
            if f.suffix in (".md", ".py"):
                yield f


def _build_artifact_path(office_dir: Path) -> Path:
    """The canonical location of the generated artifact."""
    return Path(office_dir).resolve() / "build" / "run.py"


def is_build_stale(office_dir: Path) -> bool:
    """True iff ``build/run.py`` is missing or older than any source.

    Wiring errors (missing role, etc.) surface from ``_build_tree``;
    we let them propagate so callers can wrap with friendly messages.
    """
    artifact = _build_artifact_path(office_dir)
    if not artifact.exists():
        return True
    art_mtime = artifact.stat().st_mtime
    for src in _office_tree_files(office_dir):
        if src.stat().st_mtime > art_mtime:
            return True
    return False


# ── dsl build ─────────────────────────────────────────────────────────


def cli_build(
    office_dir: Path,
    *,
    out: Optional[object] = None,
) -> int:
    """Run codegen and report. Returns a CLI exit code (0 on success).

    Parameters
    ----------
    office_dir
        The office directory to build.
    out
        File-like for status output. Defaults to ``sys.stdout``.
        Errors always go to ``sys.stderr``.
    """
    fout = out or sys.stdout
    try:
        artifact = emit_run_py(office_dir)
    except ParseError as exc:
        print(f"dsl build: {exc}", file=sys.stderr)
        return 1
    except CompileError as exc:
        print(f"dsl build: {exc}", file=sys.stderr)
        return 1

    print(f"  Wrote {artifact}", file=fout)
    print(f"  Run with:  python {artifact}", file=fout)
    print(f"        or:  dsl run {office_dir}", file=fout)
    return 0


# ── dsl run ───────────────────────────────────────────────────────────


def cli_run(office_dir: Path) -> int:
    """Rebuild if stale, then execute ``build/run.py``.

    Returns a CLI exit code. ``KeyboardInterrupt`` from the running
    network (a student pressing Ctrl-C) returns 0 — that is the
    expected way to stop a continuous office.
    """
    office_dir = Path(office_dir).resolve()

    try:
        stale = is_build_stale(office_dir)
    except (ParseError, CompileError) as exc:
        print(f"dsl run: {exc}", file=sys.stderr)
        return 1

    if stale:
        try:
            artifact = emit_run_py(office_dir)
        except (ParseError, CompileError) as exc:
            print(f"dsl run: {exc}", file=sys.stderr)
            return 1
        print(f"  Rebuilt {artifact}")
    else:
        artifact = _build_artifact_path(office_dir)

    # runpy.run_path with run_name="__main__" makes the artifact's
    # ``if __name__ == "__main__":`` block fire — the same behaviour
    # the student would get from ``python build/run.py``.
    try:
        runpy.run_path(str(artifact), run_name="__main__")
    except KeyboardInterrupt:
        return 0
    return 0


__all__ = [
    "cli_build",
    "cli_run",
    "is_build_stale",
]
