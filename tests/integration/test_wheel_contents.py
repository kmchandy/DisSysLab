"""Regression test: the built wheel must include every file that dsl
needs at run time.

History
-------

The v1.3.4 release shipped a wheel that omitted ``dissyslab/roles/``
entirely. Any office referencing a library role (entity_extractor,
severity_classifier, writer, ...) failed at compile time with
"no such role in the library". The root cause was a ``package-data``
glob that read like it covered ``.md`` files everywhere under
``dissyslab/`` but actually didn't, because setuptools' globs don't
recurse into directories that aren't already declared as packages.

This test rebuilds the wheel in a temp directory and asserts every
critical file path is present in the zip. It is intentionally
exhaustive: each new directory of shipped content gets a dedicated
assertion so a future regression names exactly what got dropped.

Mark
----

The test is marked ``slow`` because ``python -m build`` takes ~15
seconds. Skip via ``pytest -m "not slow"`` for fast inner-loop runs.
The release workflow MUST run this test before uploading to PyPI.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest


# Files we expect inside the wheel under the ``dissyslab/`` package
# root. Glob-style: ``*`` matches one path component, ``**`` matches
# any number. Each entry must match at least one zip member.
REQUIRED_FILE_GLOBS = [
    # --- Built-in role library ---------------------------------------------
    # The v1.3.4 bug: these were the files that went missing.
    "dissyslab/roles/entity_extractor.md",
    "dissyslab/roles/severity_classifier.md",
    "dissyslab/roles/urgency_classifier.md",
    "dissyslab/roles/sentiment_classifier.md",
    "dissyslab/roles/topic_tagger.md",
    "dissyslab/roles/geolocator.md",
    "dissyslab/roles/summarizer.md",
    "dissyslab/roles/summary_writer.md",
    "dissyslab/roles/relevance_filter.md",
    "dissyslab/roles/category_classifier.md",
    "dissyslab/roles/evaluator.md",
    "dissyslab/roles/writer.md",

    # --- fn_lib (Python module — ships via setuptools.find) ---------------
    "dissyslab/fn_lib/__init__.py",
    "dissyslab/fn_lib/dedup.py",

    # --- Gallery: representative offices from both tiers ------------------
    # Tier 1 (no-key, the ten-second demo).
    "dissyslab/gallery/apps/periodic_brief/office.md",
    "dissyslab/gallery/apps/periodic_brief/README.md",
    # periodic_brief's HTML sink lives alongside the office, not under
    # dissyslab/components/sinks/ (it used to, before the move in
    # "v1.4.x: app-specific sinks live in gallery app folders").
    "dissyslab/gallery/apps/periodic_brief/sinks/periodic_brief_html_sink.py",
    "dissyslab/gallery/apps/weather_monitor/office.md",
    "dissyslab/gallery/apps/stocks_monitor/office.md",

    # Tier 2 (the headline office).
    "dissyslab/gallery/apps/situation_room/office.md",
    "dissyslab/gallery/apps/situation_room/README.md",

    # Tier 2 (the per-role-override demo with a .py role file).
    "dissyslab/gallery/apps/situation_room_pro/office.md",
    "dissyslab/gallery/apps/situation_room_pro/roles/writer.py",

    # --- Gallery: every shipped office ------------------------------------
    # Generated 2026-08-17. A wheel that omits an office breaks `dsl init`
    # for it and makes the course catalogue a lie -- 10 offices were absent
    # from 1.6.1 this way. One line per office so a regression names which.
    "dissyslab/gallery/apps/adaptive_tutor/office.md",
    "dissyslab/gallery/apps/arxiv_radar/office.md",
    "dissyslab/gallery/apps/backyard_birds/office.md",
    "dissyslab/gallery/apps/competitor_watch/office.md",
    "dissyslab/gallery/apps/debate/office.md",
    "dissyslab/gallery/apps/inbox_triage/office.md",
    "dissyslab/gallery/apps/investment_club/office.md",
    "dissyslab/gallery/apps/job_hunter/office.md",
    "dissyslab/gallery/apps/kalshi_market_watch/office.md",
    "dissyslab/gallery/apps/lead_qualifier/office.md",
    "dissyslab/gallery/apps/loudness_monitor/office.md",
    "dissyslab/gallery/apps/mac_speed_suite/office.md",
    "dissyslab/gallery/apps/new_grad_jobs/office.md",
    "dissyslab/gallery/apps/paper_trader/office.md",
    "dissyslab/gallery/apps/periodic_brief/office.md",
    "dissyslab/gallery/apps/periodic_brief_pro/office.md",
    "dissyslab/gallery/apps/recovery_demo/office.md",
    "dissyslab/gallery/apps/returns_desk/office.md",
    "dissyslab/gallery/apps/room_climate_monitor/office.md",
    "dissyslab/gallery/apps/salton_sea_dashboard/office.md",
    "dissyslab/gallery/apps/shipment_release/office.md",
    "dissyslab/gallery/apps/situation_room/office.md",
    "dissyslab/gallery/apps/situation_room_pro/office.md",
    "dissyslab/gallery/apps/situation_room_requests/office.md",
    "dissyslab/gallery/apps/stocks_monitor/office.md",
    "dissyslab/gallery/apps/ticket_router/office.md",
    "dissyslab/gallery/apps/trading_room/office.md",
    "dissyslab/gallery/apps/wardrobe_assistant/office.md",
    "dissyslab/gallery/apps/weather_monitor/office.md",
    "dissyslab/gallery/apps/wildlife_watcher/office.md",

    # --- Components shipped as Python modules (not data) ------------------
    "dissyslab/components/sources/__init__.py",

    # --- Core framework entry points --------------------------------------
    "dissyslab/__init__.py",
    "dissyslab/cli.py",
    "dissyslab/office/__init__.py",
    "dissyslab/office/library.py",
    "dissyslab/backends/openrouter_backend.py",
    "dissyslab/backends/ollama_backend.py",
    "dissyslab/backends/anthropic_backend.py",
]


# Path fragments we expect to NOT appear in the wheel.
#
# Wheels namespace everything under ``dissyslab/`` (package files) or
# ``dissyslab-<version>.dist-info/`` (metadata). A repo-root directory
# like ``examples/`` can only leak into the wheel as
# ``dissyslab/examples/``, never as bare ``examples/``. So we anchor
# the forbidden top-level directories to the package prefix.
#
# Note carefully: ``dissyslab/gallery/examples/`` is a real, intended
# sub-package — it's the Builder-facing examples sub-gallery. The
# repo-root ``examples/`` directory is something else (legacy
# scratchpad) and must NOT ship. The ``dissyslab/examples/`` anchor
# below catches the second without false-firing on the first.
FORBIDDEN_PATH_FRAGMENTS = [
    "dissyslab/tests/",
    "dissyslab/dev/",
    "dissyslab/examples/",
    "dissyslab/site/",
    "dissyslab/micro_course/",
    "__pycache__/",
    ".pytest_cache/",
    ".ruff_cache/",
    ".mypy_cache/",

    # --- Generated / runtime output inside gallery apps -------------------
    # Added after v1.7.0 shipped 71 of these. They are gitignored, but
    # package-data globs read the working tree, so any machine that has
    # run an office had them sitting in the package tree at build time.
    # See GENERATED_ARTIFACTS below for the test that actually plants them.
    "/build/run.py",
    "/build/__init__.py",
    "/snapshots/",
    "/book/book.json",
]


# Generated files a real developer machine accumulates, as
# (path relative to the source root, contents) pairs. The
# ``dirty_tree_wheel`` fixture plants these before building so the
# exclusion is tested against the condition that actually caused the
# v1.7.0 leak — rather than against a clean checkout, where every such
# assertion passes vacuously.
GENERATED_ARTIFACTS = [
    ("dissyslab/gallery/apps/recovery_demo/build/run.py", "# generated\n"),
    ("dissyslab/gallery/apps/recovery_demo/build/__init__.py", ""),
    (
        "dissyslab/gallery/apps/recovery_demo/snapshots/checkpoints"
        "/000000/manifest.json",
        '{"office": "recovery_demo", "N": 0}\n',
    ),
    (
        "dissyslab/gallery/apps/paper_trader/book/book.json",
        '{"cash": 1.0, "positions": {}}\n',
    ),
    ("dissyslab/gallery/apps/situation_room/build/run.py", "# generated\n"),
]


REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def _has_build() -> bool:
    """Probe for ``python -m build``. The release env has it; CI may
    not. Skip cleanly when missing rather than red-flagging the
    suite."""
    try:
        import build  # noqa: F401
        return True
    except ImportError:
        return False


def _copy_source_tree(src: Path, dst: Path) -> None:
    """Copy the source tree to ``dst`` for an isolated build.

    Skipped paths
    -------------
    * ``.git`` — large, irrelevant to the wheel.
    * ``.venv`` / ``venv`` (at any depth) — virtual environments
      whose ``bin/python`` symlinks may dangle when copied through a
      remote mount; also irrelevant to the wheel.
    * ``build``, ``dist`` — output artifacts from prior builds; we
      want the new build to start fresh (in v1.3.x diagnosis a stale
      ``build/`` was the smoking gun on shared filesystems).
    * ``__pycache__``, ``.pytest_cache``, ``.ruff_cache``, ``.mypy_cache``
      — bytecode and tool caches.
    * ``*.egg-info`` — distutils metadata caches.

    We pass ``symlinks=True`` so any link that does slip through (e.g.
    venv ``activate`` scripts in a non-standard path) is preserved as
    a symlink rather than dereferenced — that way a broken link copies
    as a broken link instead of raising ``FileNotFoundError`` and
    aborting the whole copy.
    """
    SKIP = {
        ".git",
        ".venv",
        "venv",
        "__pycache__",
        ".pytest_cache",
        ".ruff_cache",
        ".mypy_cache",
    }

    # ``build`` and ``dist`` are skipped only at the TOP level. That is
    # the whole of the original reason for skipping them: setuptools'
    # staging directory and prior wheel output, both at the source root.
    #
    # Skipping them at every depth — which this function used to do —
    # silently deleted ``dissyslab/gallery/apps/*/build/`` on the way
    # into the test, so the wheel under test was always clean even when
    # a real ``python -m build`` in the same tree shipped those files.
    # That is why the forbidden-path test did not catch v1.7.0. The test
    # was sanitising the exact input it existed to inspect.
    TOP_LEVEL_SKIP = {"build", "dist"}
    src_resolved = src.resolve()

    def ignore(directory: str, names: list[str]) -> list[str]:
        at_top = Path(directory).resolve() == src_resolved
        return [
            n for n in names
            if n in SKIP
            or n.endswith(".egg-info")
            or (at_top and n in TOP_LEVEL_SKIP)
        ]

    shutil.copytree(src, dst, ignore=ignore, symlinks=True)


@pytest.fixture(scope="module")
def built_wheel(tmp_path_factory):
    """Build the wheel once per test module, return its zip namelist
    plus a path for further inspection.

    Why we copy the source tree first
    ---------------------------------

    setuptools writes build staging artifacts to ``<srcdir>/build/``
    even when ``python -m build`` is run with PEP 517 isolation. If
    the source tree already contains a ``build/`` from a previous run
    on a different user / OS / filesystem, the new build dies trying
    to overwrite those files. We sidestep this by copying the source
    to a per-module tmp dir and building from there — both the build
    staging and the wheel output land in tmp space we own.

    The copy adds 1–3 seconds; on a clean repo it would be wasted, but
    it makes the test work uniformly on developer Macs, CI runners,
    and the release box.
    """
    if not _has_build():
        pytest.skip("python -m build not available (install: pip install build)")

    work_root = tmp_path_factory.mktemp("wheel-build")
    src_copy = work_root / "src"
    out_dir = work_root / "dist"
    out_dir.mkdir()

    _copy_source_tree(REPO_ROOT, src_copy)

    result = subprocess.run(
        [sys.executable, "-m", "build", "--wheel", "--outdir", str(out_dir)],
        cwd=str(src_copy),
        capture_output=True,
        text=True,
        timeout=180,
    )
    if result.returncode != 0:
        pytest.fail(
            f"python -m build failed (exit {result.returncode}).\n\n"
            f"STDOUT:\n{result.stdout}\n\nSTDERR:\n{result.stderr}"
        )

    wheels = sorted(out_dir.glob("dissyslab-*.whl"))
    assert wheels, f"build produced no wheel in {out_dir}"
    wheel_path = wheels[-1]

    with zipfile.ZipFile(wheel_path) as zf:
        names = zf.namelist()

    return {"path": wheel_path, "names": names}


@pytest.mark.slow
@pytest.mark.parametrize("required_path", REQUIRED_FILE_GLOBS)
def test_wheel_includes_required_file(built_wheel, required_path):
    """Every entry in REQUIRED_FILE_GLOBS must appear in the wheel.

    Parametrised so a missing file produces a single, named test
    failure rather than a vague AssertionError listing 30 paths.
    """
    names = built_wheel["names"]
    if required_path not in names:
        candidates = [n for n in names if n.endswith(required_path.split("/")[-1])]
        hint = (
            f"\nDid you mean one of these? {candidates[:5]}"
            if candidates
            else "\n(no similarly-named file in the wheel)"
        )
        pytest.fail(
            f"Wheel is missing required path: {required_path!r}.\n"
            f"This is the bug that broke v1.3.4 — check "
            f"pyproject.toml's [tool.setuptools.package-data] globs."
            f"{hint}"
        )


@pytest.mark.slow
@pytest.mark.parametrize("forbidden", FORBIDDEN_PATH_FRAGMENTS)
def test_wheel_excludes_dev_paths(built_wheel, forbidden):
    """No test, dev, or build-cache content should ride along."""
    names = built_wheel["names"]
    leaked = [n for n in names if forbidden in n]
    assert not leaked, (
        f"Wheel leaks {forbidden!r} content: {leaked[:5]}"
        + ("..." if len(leaked) > 5 else "")
    )


@pytest.mark.slow
def test_wheel_has_minimum_role_count(built_wheel):
    """Defence in depth: regardless of which specific roles are listed
    above, we expect at least ten role files. If this count drops it
    indicates a glob regression even when the named files happen to
    still match.
    """
    role_md_files = [
        n for n in built_wheel["names"]
        if n.startswith("dissyslab/roles/") and n.endswith(".md")
    ]
    assert len(role_md_files) >= 10, (
        f"Wheel ships only {len(role_md_files)} role files; "
        f"expected at least 10. Names found: {role_md_files}"
    )


@pytest.mark.slow
def test_wheel_has_minimum_gallery_office_count(built_wheel):
    """Defence in depth: at least 12 gallery offices should ship (the
    gallery currently has more, but 12 is the floor we don't want to
    drop below silently). Each office has an office.md."""
    office_files = [
        n for n in built_wheel["names"]
        if n.startswith("dissyslab/gallery/")
        and n.endswith("/office.md")
    ]
    assert len(office_files) >= 12, (
        f"Wheel ships only {len(office_files)} gallery offices; "
        f"expected at least 12. Names found: {office_files}"
    )


# ---------------------------------------------------------------------------
# The v1.7.0 leak, tested against the condition that caused it
# ---------------------------------------------------------------------------
#
# Every assertion above runs against a clean checkout, where no generated
# output exists and "the wheel contains no build/run.py" is true for the
# uninteresting reason. The release that broke was built on a machine
# that had run the offices. So we plant that state and build again.


@pytest.fixture(scope="module")
def dirty_tree_wheel(tmp_path_factory):
    """Build a wheel from a tree that contains generated output.

    Plants the files a developer machine accumulates from running the
    gallery — ``build/run.py``, ``snapshots/``, ``book/book.json`` — and
    builds. They are all gitignored, which is precisely why they were
    invisible: setuptools' package-data globs read the working tree and
    have never consulted git.
    """
    if not _has_build():
        pytest.skip("python -m build not available (install: pip install build)")

    work_root = tmp_path_factory.mktemp("dirty-wheel-build")
    src_copy = work_root / "src"
    out_dir = work_root / "dist"
    out_dir.mkdir()

    _copy_source_tree(REPO_ROOT, src_copy)

    for rel, contents in GENERATED_ARTIFACTS:
        target = src_copy / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(contents)

    result = subprocess.run(
        [sys.executable, "-m", "build", "--wheel", "--outdir", str(out_dir)],
        cwd=str(src_copy),
        capture_output=True,
        text=True,
        timeout=180,
    )
    if result.returncode != 0:
        pytest.fail(
            f"python -m build failed (exit {result.returncode}).\n\n"
            f"STDOUT:\n{result.stdout}\n\nSTDERR:\n{result.stderr}"
        )

    wheels = sorted(out_dir.glob("dissyslab-*.whl"))
    assert wheels, f"build produced no wheel in {out_dir}"

    with zipfile.ZipFile(wheels[-1]) as zf:
        names = zf.namelist()

    return {"path": wheels[-1], "names": names, "planted": GENERATED_ARTIFACTS}


@pytest.mark.slow
@pytest.mark.parametrize(
    "planted_path", [rel for rel, _ in GENERATED_ARTIFACTS]
)
def test_generated_output_does_not_ship(dirty_tree_wheel, planted_path):
    """A build from a tree with generated output must not carry it.

    Guarded by ``[tool.setuptools.exclude-package-data]`` in
    pyproject.toml. If this fails, check that block first — and note
    that adding a *new* kind of generated directory under a gallery app
    needs a new exclusion, since the include globs match everything.
    """
    if planted_path in dirty_tree_wheel["names"]:
        pytest.fail(
            f"Wheel ships generated output: {planted_path!r}.\n"
            f"This is the v1.7.0 bug — that release shipped 71 such "
            f"files, and `dsl init` copied them into every student's "
            f"folder. Fix the [tool.setuptools.exclude-package-data] "
            f"globs in pyproject.toml."
        )


@pytest.mark.slow
def test_dirty_tree_wheel_still_complete(dirty_tree_wheel):
    """The exclusions must not overshoot.

    ``gallery/apps/*/build/*`` and friends sit next to files we very
    much do ship. A too-greedy exclusion that also dropped office.md
    would pass every test above (they run on the clean build) while
    breaking `dsl init` for real users.
    """
    offices = [
        n for n in dirty_tree_wheel["names"]
        if n.startswith("dissyslab/gallery/") and n.endswith("/office.md")
    ]
    assert len(offices) >= 12, (
        f"Exclusions overshot: dirty-tree wheel ships only "
        f"{len(offices)} offices."
    )
    for required in (
        "dissyslab/gallery/apps/recovery_demo/office.md",
        "dissyslab/gallery/apps/paper_trader/office.md",
        "dissyslab/gallery/apps/wardrobe_assistant/wardrobe_inventory.json",
    ):
        assert required in dirty_tree_wheel["names"], (
            f"Exclusions dropped a file we ship: {required!r}"
        )
