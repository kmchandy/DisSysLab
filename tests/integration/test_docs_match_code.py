"""Mechanical checks that the prose matches the code.

Why this file exists
--------------------

A student walk-through on 2026-08-17 produced eleven issues. Six were
the same failure wearing different clothes: **a document asserted
something about the system that the system does not do, and nothing
detected the divergence.**

- The skill mandated ``dsl check`` before every run. ``dsl check`` did
  not exist in the released wheel. A student's agent responded by
  trying to patch ``site-packages``.
- ``START_HERE`` catalogued 38 examples. A wheel install could reach 28.
- ``SOURCES_AND_SINKS.md`` documented ``salton_wind``. There is no
  such registered source.
- The generic ``rss(url=...)`` source existed only in a docstring, so
  the catalogue read as though adding a feed required changing the
  framework.

None of these is subtle. Each survived because checking it meant a
human re-reading prose against code, and nobody does that on every
commit. All four are decidable by a machine in milliseconds.

``dsl check`` does exactly this for offices — it compares what an
``office.md`` claims against what the registries hold. These tests do
it for the documentation. The principle is the same one the course
teaches: *the assertion and the thing asserted must be checked
together, mechanically, or they drift.*

What each test covers
---------------------

============  =========================================================
Test          Issue it would have caught
============  =========================================================
sources/sinks B2 (``rss`` undocumented), and the ``salton_wind`` promise
subcommands   A1 (skill mandates a command absent from the release)
catalogue     A2 / B5 (catalogue lists offices the wheel does not ship)
============  =========================================================

On failure, prefer fixing the *document*. These tests encode "the
prose is a promise to a first-year", not "the code is right".
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SOURCES_DOC = REPO_ROOT / "docs" / "SOURCES_AND_SINKS.md"
START_HERE = REPO_ROOT / "course" / "START_HERE.md"
CLI_PY = REPO_ROOT / "dissyslab" / "cli.py"


# ---------------------------------------------------------------------------
# 1. Sources and sinks: the doc and the registry must agree, both ways
# ---------------------------------------------------------------------------
#
# Both directions matter, and they fail differently.
#
#   doc -> registry   The doc promises a component that does not exist.
#                     A student writes it into office.md and gets a
#                     compile error naming something they copied from
#                     our own catalogue.
#
#   registry -> doc   A component exists and nobody can find it. This
#                     is quieter and cost more: `rss(url=...)` was
#                     registered and worked, but appeared only in a
#                     Python docstring, so the catalogue's "adding a new
#                     one is close to a one-line change" read as an
#                     invitation to patch the framework.


# Registry entries deliberately absent from the student-facing
# catalogue. Every entry needs a reason, and "we never got round to it"
# is not one — if that is the true reason, document the component
# instead of adding it here.
UNDOCUMENTED_BY_DESIGN: dict[str, str] = {
    # App-local sinks: registered so one gallery office can name them,
    # not offered as general-purpose building blocks. A student meets
    # these by reading the app that uses them.
    #
    # Note on how narrow "app-local" has to be. `markdown_digest` and
    # `report_html` were on this list, justified as app-local to
    # competitor_watch and salton_sea_dashboard. That was wrong, and the
    # E5 trial proved it: an agent building a competitor digest reached
    # for `markdown_digest`, found no arguments documented anywhere, and
    # guessed `path=`. It guessed right and still shipped a report
    # headed "Morning digest", because `title` defaults to that and
    # nothing said so. A sink belonging to an app students are told to
    # copy is not app-local. Both are documented now.
    #
    # The remaining entries are sinks whose output shape only makes
    # sense inside one office -- a student meets them by reading that
    # office, not by choosing from a catalogue.
    "debate_display": "renders debate's turn structure; meaningless elsewhere",
    "job_html_sink": "renders job_hunter's match records",
    "tutor_session_display": "renders adaptive_tutor's session state",
    "intelligence_display": "renders situation_room's briefing records",
    "periodic_brief_sink": "app-local to periodic_brief",
    "periodic_brief_html_sink": "app-local to periodic_brief",
    # Test and demo scaffolding, not something to build with.
    "csv_points_source": "fixture for recovery_demo's pi estimate",
    "session_starter": "internal: seeds a session-shaped office",
}


def _numbered_variant_base(name: str) -> str | None:
    """``stocks_3`` -> ``stocks``. Otherwise ``None``.

    The registry holds numbered clones of several components so one
    office can instantiate the same source more than once under
    distinct names. Documenting ``stocks_2`` through ``stocks_5``
    separately would pad the catalogue with four entries that say
    "same as above". The base entry documents the family.
    """
    m = re.fullmatch(r"(.+)_(\d+)", name)
    return m.group(1) if m else None


def _suffixed_variant_base(name: str, documented: set[str]) -> str | None:
    """``slack_sink_alerts`` -> ``slack_sink``, when the base is itself
    documented. Same reasoning as the numbered variants: the doc has a
    ``jsonl_recorder_*`` section covering the whole family.

    Only the *longest* documented prefix counts, so ``gmail_sink_match``
    resolves to ``gmail_sink`` rather than accidentally to ``gmail``.
    """
    best = None
    for base in documented:
        if name.startswith(base + "_") and (best is None or len(base) > len(best)):
            best = base
    return best


def _registries():
    from dissyslab.office.utils import SOURCE_REGISTRY, SINK_REGISTRY
    return SOURCE_REGISTRY, SINK_REGISTRY


def _doc_text() -> str:
    return SOURCES_DOC.read_text(encoding="utf-8")


def _promised_names(doc: str) -> set[str]:
    """Names the doc presents *as components a student may write*.

    Deliberately structural rather than "every backticked token": the
    doc backticks argument names, file names, and code fragments too,
    and treating those as promises would make this test noise. Two
    positions count as a promise:

    * a section heading — ``### `weather` — current weather``
    * the first cell of a catalogue table row — ``| `hacker_news` | ...``
    """
    headings = set(re.findall(r"^#{2,4}\s+`([a-z0-9_]+)`", doc, re.M))
    table_rows = set(re.findall(r"^\|\s*`([a-z0-9_]+)`\s*\|", doc, re.M))
    return headings | table_rows


def _not_yet_registered(doc: str) -> set[str]:
    """Components the doc describes while saying they do not work yet.

    A documented plan is not a broken promise, as long as the document
    says which it is. ``salton_wind`` has an implementation and no
    registry entry; describing it is useful, and the heading says
    plainly that ``Sources: salton_wind`` will not compile.

    The marker must be in the *heading*, not the body, so a reader
    scanning the contents cannot miss it — and so this exemption cannot
    be granted by a sentence buried three paragraphs down.
    """
    return set(
        re.findall(
            r"^#{2,4}\s+`([a-z0-9_]+)`[^\n]*not yet registered",
            doc,
            re.M | re.I,
        )
    )


def _mentioned_names(doc: str) -> set[str]:
    """Every backticked identifier anywhere in the doc.

    Loose on purpose. This side of the comparison asks only "could a
    student find this name by reading the catalogue?", and a mention in
    an example counts.
    """
    return set(re.findall(r"`([a-z0-9_]+)`", doc))


@pytest.mark.parametrize("kind", ["sources", "sinks"])
def test_doc_promises_only_components_that_exist(kind):
    """Every component the catalogue presents must be in the registry."""
    sources, sinks = _registries()
    registry = sources if kind == "sources" else sinks
    both = set(sources) | set(sinks)

    doc = _doc_text()
    # A heading may legitimately cover a family with a wildcard
    # (``jsonl_recorder_*``); the regex above already excludes those,
    # since ``*`` is not in the character class.
    promised = _promised_names(doc)

    # Restrict to the half of the doc this parametrisation owns, so a
    # failure names the right registry. Sinks live after the '## Sinks'
    # heading; everything before it is sources.
    split = doc.index("\n## Sinks")
    section = doc[:split] if kind == "sources" else doc[split:]
    promised_here = promised & _promised_names(section)
    promised_here -= _not_yet_registered(doc)

    missing = sorted(n for n in promised_here if n not in both)
    assert not missing, (
        f"{SOURCES_DOC.name} documents {kind} that are not registered: "
        f"{missing}.\n"
        f"A student who copies one of these out of our own catalogue "
        f"gets a compile error. Either register the component, remove "
        f"the section, or -- if it is a real plan -- add 'not yet "
        f"registered' to the heading so the doc says so out loud.\n"
        f"Registered {kind}: {sorted(registry)}"
    )


@pytest.mark.parametrize("kind", ["sources", "sinks"])
def test_every_registered_component_is_findable_in_the_doc(kind):
    """Every registry entry must be reachable by reading the catalogue.

    A component nobody can find is, from a first-year's position,
    a component that does not exist — except worse, because the
    catalogue's silence reads as "this is not possible" rather than
    "look elsewhere".
    """
    sources, sinks = _registries()
    registry = sources if kind == "sources" else sinks

    doc = _doc_text()
    mentioned = _mentioned_names(doc)
    documented_bases = _promised_names(doc)

    undocumented = []
    for name in sorted(registry):
        if name in mentioned or name in UNDOCUMENTED_BY_DESIGN:
            continue
        base = _numbered_variant_base(name)
        if base and (base in mentioned or base in documented_bases):
            continue
        base = _suffixed_variant_base(name, documented_bases)
        if base:
            continue
        undocumented.append(name)

    assert not undocumented, (
        f"These {kind} are registered but appear nowhere in "
        f"{SOURCES_DOC.name}: {undocumented}.\n"
        f"A student cannot use what the catalogue does not mention. "
        f"Document them, or — if one is genuinely app-local or "
        f"internal — add it to UNDOCUMENTED_BY_DESIGN in this file "
        f"with the reason."
    )


# ---------------------------------------------------------------------------
# 2. Every `dsl` subcommand named in a skill or course doc must exist
# ---------------------------------------------------------------------------
#
# This is issue A1, and it is the one that did real damage. The skill
# instructed the agent to run `dsl check` before every office. The
# released wheel had no `check` subcommand. The agent, told to do
# something impossible by a document it trusted, went looking for a way
# to make it possible -- and started editing the user's site-packages.
#
# A version guard now handles the *runtime* case (26abd4a). This test
# handles the case the guard cannot: a command that never existed at
# all, or one renamed out from under the docs.


def _doc_files() -> list[Path]:
    roots = [REPO_ROOT / "skills", REPO_ROOT / "course"]
    return [p for r in roots if r.exists() for p in r.rglob("*.md")]


def _cli_subcommands() -> set[str]:
    cli = CLI_PY.read_text(encoding="utf-8")
    return set(re.findall(r"add_parser\(\s*['\"]([a-z_-]+)['\"]", cli))


# Words that follow `dsl` in prose without naming a subcommand.
_NOT_A_SUBCOMMAND = {
    "and", "are", "as", "at", "by", "can", "command", "commands", "does",
    "for", "from", "has", "in", "is", "it", "itself", "of", "on", "or",
    "reads", "reports", "runs", "subcommand", "subcommands", "that",
    "the", "to", "will", "with", "writes", "you",
}


def test_documented_dsl_subcommands_exist():
    subcommands = _cli_subcommands()
    assert subcommands, "parsed no subcommands out of cli.py — check the regex"

    bad: dict[str, set[str]] = {}
    for path in _doc_files():
        text = path.read_text(encoding="utf-8")
        for word in re.findall(r"\bdsl\s+([a-z][a-z-]*)\b", text):
            if word in subcommands or word in _NOT_A_SUBCOMMAND:
                continue
            bad.setdefault(word, set()).add(
                str(path.relative_to(REPO_ROOT))
            )

    assert not bad, (
        "These docs name `dsl` subcommands that do not exist in "
        "cli.py:\n"
        + "\n".join(
            f"  dsl {w} — {sorted(files)}" for w, files in sorted(bad.items())
        )
        + f"\n\nReal subcommands: {sorted(subcommands)}\n"
        "This is issue A1. A skill that mandates an impossible command "
        "does not produce a clean failure — it produces an agent "
        "improvising, and in the observed case editing site-packages."
    )


# ---------------------------------------------------------------------------
# 3. Every office in START_HERE's catalogue must actually ship
# ---------------------------------------------------------------------------
#
# Issues A2 and B5. START_HERE catalogued 38 examples; the 1.6.1 wheel
# shipped 28. A student picking a project from the catalogue had a
# roughly one-in-four chance of picking one they could not run, and no
# way to tell which.
#
# tests/integration/test_wheel_contents.py asserts each office is in
# the built wheel. This asserts the catalogue and the gallery name the
# same set -- the other half of the same promise.


def _catalogue_names() -> set[str]:
    """Office names from START_HERE's catalogue section.

    Scoped to section 5 so that `office.md`, `dsl run` and similar
    backticked tokens elsewhere in the document are not mistaken for
    office names.
    """
    text = START_HERE.read_text(encoding="utf-8")
    m = re.search(r"^## 5\.[^\n]*\n(.*?)(?=^## )", text, re.M | re.S)
    assert m, "could not find section 5 (the catalogue) in START_HERE.md"
    body = m.group(1)

    # Only *entry positions* count, not every backtick in the section.
    # The catalogue writes an entry as a name at the start of a line, or
    # after a middot when several share one description, or bolded in
    # the first cell of the teaching-shapes table. Anything else is
    # commentary -- and commentary names real things that are not
    # offices: `backyard_birds` is an entry, the `birdnetlib` in its
    # description is a PyPI package.
    names: set[str] = set()
    names |= set(re.findall(r"^\*{0,2}`([a-z][a-z0-9_]+)`", body, re.M))
    names |= set(re.findall(r"·\s*\*{0,2}`([a-z][a-z0-9_]+)`", body))
    names |= set(re.findall(r"^\|\s*\*{0,2}`([a-z][a-z0-9_]+)`", body, re.M))
    return names


def _shipped_offices() -> set[str]:
    """Every office a student can reach, by the same rule the CLI uses.

    `network.md` counts as well as `office.md`. A multi-office app --
    `org_two_office_news` is the one that exists -- has a `network.md`
    at its root and the individual `office.md` files one level further
    down, so a check that looks only for `office.md` does not see it at
    all. `dissyslab/cli.py`'s `_find_packaged_office` accepts both, so
    a rule here that accepts only one is narrower than the thing it is
    checking, and would report the app as uncatalogued the moment
    anyone added it to START_HERE.
    """
    import dissyslab.gallery as gallery
    root = Path(gallery.__file__).parent
    names = set()
    for sub in ("apps", "examples"):
        d = root / sub
        if d.is_dir():
            names |= {
                c.name for c in d.iterdir()
                if (c / "office.md").exists() or (c / "network.md").exists()
            }
    return names


def test_start_here_catalogue_matches_the_gallery():
    catalogued = _catalogue_names()
    shipped = _shipped_offices()
    assert shipped, "found no shipped offices — is dissyslab importable?"

    missing = sorted(catalogued - shipped)
    assert not missing, (
        f"START_HERE.md catalogues offices that are not installed: "
        f"{missing}.\n"
        f"Installed: {sorted(shipped)}.\n"
        f"If you are running against an editable install this means the "
        f"catalogue is wrong; against a wheel it may instead mean the "
        f"office did not ship — check "
        f"tests/integration/test_wheel_contents.py."
    )


# ---------------------------------------------------------------------------
# 4. Every .skill bundle must match the directory it was built from
# ---------------------------------------------------------------------------
#
# The bundle is a zip of the source directory, built by hand. Edit a
# reference, forget to repackage, send the bundle, and the installed
# skill is a version that exists nowhere in git -- with no error, because
# both files are individually fine. This already cost a full test round
# once: an old bundle was installed and the wrong skill ran throughout.
#
# Same shape as everything else in this file. Two artifacts that are
# supposed to say the same thing, and nothing checking that they do.


def _skill_bundles() -> list[Path]:
    d = REPO_ROOT / "skills"
    return sorted(d.glob("*.skill")) if d.is_dir() else []


def test_there_is_at_least_one_skill_bundle():
    """Guards the parametrisation below: zero bundles would make every
    bundle test pass by having nothing to run."""
    assert _skill_bundles(), "no .skill bundles found under skills/"


@pytest.mark.parametrize(
    "bundle", _skill_bundles(), ids=lambda p: p.name
)
def test_skill_bundle_matches_its_source_directory(bundle):
    import zipfile

    source_dir = bundle.with_suffix("")
    assert source_dir.is_dir(), (
        f"{bundle.name} has no matching source directory "
        f"{source_dir.name}/"
    )

    with zipfile.ZipFile(bundle) as zf:
        bundled = {
            i.filename: zf.read(i.filename)
            for i in zf.infolist()
            if not i.is_dir()
        }

    on_disk = {
        f"{source_dir.name}/{p.relative_to(source_dir).as_posix()}": p.read_bytes()
        for p in sorted(source_dir.rglob("*"))
        if p.is_file() and "__pycache__" not in p.parts
        and p.name != ".DS_Store"
    }

    missing = sorted(set(on_disk) - set(bundled))
    extra = sorted(set(bundled) - set(on_disk))
    stale = sorted(
        n for n in set(bundled) & set(on_disk) if bundled[n] != on_disk[n]
    )

    assert not (missing or extra or stale), (
        f"{bundle.name} is out of date with {source_dir.name}/.\n"
        + (f"  missing from bundle: {missing}\n" if missing else "")
        + (f"  in bundle but not on disk: {extra}\n" if extra else "")
        + (f"  contents differ: {stale}\n" if stale else "")
        + f"\nRepackage:  cd skills && rm -f {bundle.name} && "
        f"zip -r {bundle.name} {source_dir.name} "
        f'-x "*.DS_Store" "*__pycache__*"'
    )


@pytest.mark.parametrize(
    "bundle", _skill_bundles(), ids=lambda p: p.name
)
def test_skill_declares_a_version_string(bundle):
    """A skill must be able to say which version it is.

    An install can report success while the previous version stays
    resident, and without a marker in the text there is no way to tell
    from the outside — you can only guess from behaviour. The marker
    makes "did the update take?" a question with an answer.
    """
    skill_md = bundle.with_suffix("") / "SKILL.md"
    assert skill_md.exists(), f"{bundle.name}: no SKILL.md in source dir"
    text = skill_md.read_text(encoding="utf-8")
    assert re.search(r"Skill version: `\d{4}-\d{2}-\d{2}[a-z]?\.[0-9a-f]{7}`", text), (
        f"{skill_md.relative_to(REPO_ROOT)} declares no version string.\n"
        "Expected a line near the top of the form\n"
        "  **Skill version: `YYYY-MM-DD.<7-hex>`.**\n"
        "Generate it with:  python scripts/stamp_skills.py"
    )


@pytest.mark.parametrize(
    "bundle", _skill_bundles(), ids=lambda p: p.name
)
def test_skill_version_matches_its_content(bundle):
    """The version must be *derived*, not merely present.

    The previous test asserts a string exists. That is not enough, and
    the gap was demonstrated the day it was written: the skill was edited
    three times on 2026-08-17 and the string stayed `2026-08-17b`
    throughout, so the marker added that morning to make installs
    verifiable could not distinguish the three versions — and this
    suite stayed green, because a string was indeed present.

    An assertion that cannot fail usefully is the same defect as the
    documents §F is about, wearing a test's clothes. So the hash half of
    the version is computed from the skill's own bytes, and this checks
    it. Edit anything, forget to re-stamp, and the failure names the
    skill.
    """
    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    try:
        from stamp_skills import content_hash, current_stamp
    finally:
        sys.path.pop(0)

    source_dir = bundle.with_suffix("")
    found = current_stamp(source_dir / "SKILL.md")
    assert found is not None, f"{source_dir.name}: no version line"
    date, declared = found
    expected = content_hash(source_dir)
    assert declared == expected, (
        f"{source_dir.name}'s version is stale: declares "
        f"{date}.{declared}, content hashes to {expected}.\n"
        f"Run:  python scripts/stamp_skills.py && "
        f"cd skills && rm -f {bundle.name} && "
        f"zip -r {bundle.name} {source_dir.name} "
        f'-x "*.DS_Store" "*__pycache__*"'
    )


# ---------------------------------------------------------------------------
# 5. Every substantial module has an entry in the internals README
# ---------------------------------------------------------------------------
#
# `docs/internals/README.md` pairs an overview and an implementation note
# with each module, and is the map a maintainer reads first. `os_agent.py`
# -- 450 lines, and the module that decides when an office stops -- was
# missing from it for months, which nobody noticed because nothing looks.
#
# Same shape as everything else in this file: a document that claims to
# list the modules, and no check that it does.


# Modules that need no entry, each with a reason. Small, obvious, or
# covered by another module's note.
MODULES_WITHOUT_DOCS: dict[str, str] = {
    "__init__.py": "re-exports only",
    "cli.py": "the user-facing surface; documented in course/ and README",
    "cli_chat.py": "thin wrapper over cli",
    "snapshot.py": "covered by os_agent_implementation and the algorithm docs",
    "utils.py": "grab-bag; no single subject to document",
    "builder.py": "has its own pair already",
    "roles_catalogue.py": (
        "the front-matter format and why each role must say what it "
        "emits are in its own docstring; what a user does with it is "
        "`dsl roles`, documented in the skill's role reference where "
        "someone choosing a role is reading"
    ),
    "market_fetch.py": (
        "one command's worth of logic, and the reasoning -- why it is a "
        "subcommand an assistant can run rather than a script in a "
        "gallery folder -- is in its own docstring and in "
        "docs/SOURCES_AND_SINKS.md, which is where a person looking for "
        "market data reads"
    ),
    "market_data.py": (
        "one rule -- where a user's own price files live -- and its own "
        "docstring carries the reasoning. The part worth documenting is "
        "that nothing here ships market data, which is in "
        "docs/SOURCES_AND_SINKS.md and pyproject.toml where the "
        "constraint bites"
    ),
    "skills_installed.py": (
        "one question with one answer -- which DisSysLab skills are on "
        "this machine. Its own docstring carries the reasoning, and the "
        "part worth documenting is the *decision* not to ask the "
        "assistant, which belongs in course/SETUP.md where the person "
        "following the steps will read it"
    ),
}


def _top_level_modules() -> list[str]:
    pkg = REPO_ROOT / "dissyslab"
    return sorted(
        p.name for p in pkg.glob("*.py")
        if not p.name.startswith("_") or p.name == "__init__.py"
    )


def test_internals_readme_lists_every_substantial_module():
    readme = REPO_ROOT / "docs" / "internals" / "README.md"
    text = readme.read_text(encoding="utf-8")

    missing = []
    for name in _top_level_modules():
        if name in MODULES_WITHOUT_DOCS:
            continue
        if f"dissyslab/{name}" not in text:
            missing.append(name)

    assert not missing, (
        f"docs/internals/README.md does not mention: {missing}.\n"
        f"It is the map a maintainer reads first, so a module absent "
        f"from it is a module nobody is told exists. Write the pair, or "
        f"— if it genuinely needs none — add it to MODULES_WITHOUT_DOCS "
        f"in this file with the reason."
    )


def test_the_internals_readme_does_not_point_at_missing_files():
    """The other direction: a link to a document that was never written
    is worse than no link, because it reads as though the document is
    somewhere and the reader simply cannot find it."""
    readme = REPO_ROOT / "docs" / "internals" / "README.md"
    text = readme.read_text(encoding="utf-8")
    linked = set(re.findall(r"\]\((?!\.\./|https?:)([A-Za-z0-9_./-]+\.md)\)", text))

    broken = sorted(
        name for name in linked
        if not (readme.parent / name).exists()
    )
    assert not broken, (
        f"docs/internals/README.md links to files that do not exist: "
        f"{broken}"
    )


# ---------------------------------------------------------------------------
# 6. Every relative link in every document must resolve
# ---------------------------------------------------------------------------
#
# The README's link check (section 5) covers one file. This covers all of
# them, and it exists because the folders are about to be reorganised: a
# move that breaks a link should fail here rather than be discovered by a
# student following it.
#
# It found sixteen already broken before a single file moved — including
# `situation_room/README.md` pointing at `../../../docs/BUILD_APPS.md`
# when the gallery app is four levels down, not three. That link has been
# dead for as long as the file has existed, and it is in the README of the
# office the course calls its workhorse.


_DOC_EXTENSIONS = {
    ".md", ".py", ".png", ".gif", ".jpg", ".html", ".csv", ".txt",
    ".sh", ".toml", ".yml", ".yaml", ".jsonl", ".json", ".ics",
}

_MD_LINK = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")

# GitHub renders raw HTML inside markdown, and the README uses an <img>
# tag rather than `![]()` so it can set a width. A moved image breaks it
# *silently* — the page still renders, with a broken-image box — which is
# worse than a dead text link, so it is checked too.
_HTML_SRC = re.compile(r"""<img\b[^>]*\bsrc\s*=\s*["']([^"']+)["']""", re.I)


def _looks_like_a_path(target: str) -> bool:
    """Distinguish a file link from prose in brackets.

    Role prompts contain things like ``[label](url)`` as a *template* for
    a model to fill in, and `wardrobe_assistant` writes server routes like
    ``/api/offices/...`` that are URLs at run time, not files on disk.
    Neither is a link into the repository, and treating them as one would
    make this test noise — which is how checks get deleted.
    """
    if target.startswith("/"):
        return False                       # a server route, not a repo path
    if "/" in target:
        return True
    return pathlib_suffix(target) in _DOC_EXTENSIONS


def pathlib_suffix(name: str) -> str:
    return Path(name).suffix.lower()


def _markdown_files() -> list[Path]:
    import subprocess

    out = subprocess.run(
        ["git", "ls-files", "*.md"],
        cwd=REPO_ROOT, capture_output=True, text=True,
    ).stdout.split()
    return [
        REPO_ROOT / f for f in out
        # archive/ is kept deliberately stale — its documents are
        # snapshots of a past state and their links are allowed to rot.
        if not f.startswith("archive/")
    ]


def test_every_relative_link_resolves():
    broken: dict[str, list[str]] = {}

    for path in _markdown_files():
        text = path.read_text(encoding="utf-8", errors="replace")
        for raw in _MD_LINK.findall(text) + _HTML_SRC.findall(text):
            target = raw.split()[0].strip("<>")
            if target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            if not _looks_like_a_path(target):
                continue
            resolved = (path.parent / target.split("#")[0]).resolve()
            if not resolved.exists():
                key = str(path.relative_to(REPO_ROOT))
                broken.setdefault(key, []).append(target)

    assert not broken, (
        "These documents link to files that do not exist:\n"
        + "\n".join(
            f"  {f}\n" + "\n".join(f"      -> {t}" for t in targets)
            for f, targets in sorted(broken.items())
        )
        + "\n\nA dead link is worse than no link: it reads as though the "
        "document exists and the reader simply cannot find it."
    )


# ---------------------------------------------------------------------------
# 7. Source comments point at documents too, and nothing was checking those
# ---------------------------------------------------------------------------
#
# Section 6 reads markdown. But a docstring saying "see
# docs/internals/design/termination_detection_design.md §6" is a link
# with the same job and the same failure mode, and a reorganisation
# breaks it just as silently -- more silently, in fact, since nobody
# clicks a docstring and finds a 404. The reader goes looking and gives
# up. (That path is written out in full on purpose: this check reads
# its own explanation, so the example has to be a live one.)
#
# The rule is deliberately narrow, because a noisy check gets deleted.
# Only a reference that begins with one of the repository's top-level
# directories is judged: those are unambiguously repo-rooted, so
# "does it exist" is a well-posed question. Prose like `roles/<name>.md`,
# `office.md`, or a hypothetical `my_office/roles/entity_extractor.py`
# is not a claim about this repository and is left alone.

_SOURCE_REF = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_./-]*\.(?:md|py)")

# A reference is checkable only if it starts with one of these.
_REPO_TOP_LEVEL = (
    "docs/", "course/", "skills/", "scripts/", "tests/", "archive/",
    "dissyslab/",
    # dev/ is maintainer scratch and is not in the repository. That is
    # exactly why a shipped docstring must not send a reader there.
    "dev/",
)


def _is_a_checkable_reference(token: str) -> bool:
    if not token.startswith(_REPO_TOP_LEVEL):
        return False
    if "..." in token or "<" in token or ">" in token:
        return False                       # an elision or a placeholder
    if re.search(r"(^|/)build/", token):
        return False                       # codegen output; never on disk
    # `dissyslab/roles/X.md` and friends: a single-letter stem is the
    # library's way of writing "some role", not a filename.
    if any(len(seg) == 1 and seg.isupper() for seg in token.split("/")):
        return False
    if len(Path(token).stem) == 1:
        return False
    return True


def test_every_document_referenced_from_source_exists():
    import subprocess

    sources = subprocess.run(
        ["git", "ls-files", "*.py"],
        cwd=REPO_ROOT, capture_output=True, text=True,
    ).stdout.split()

    broken: dict[str, list[str]] = {}
    for rel in sources:
        path = REPO_ROOT / rel
        text = path.read_text(encoding="utf-8", errors="replace")
        for token in sorted(set(_SOURCE_REF.findall(text))):
            if not _is_a_checkable_reference(token):
                continue
            if not (REPO_ROOT / token).exists():
                broken.setdefault(rel, []).append(token)

    assert not broken, (
        "These source files point at documents that do not exist:\n"
        + "\n".join(
            f"  {f}\n" + "\n".join(f"      -> {t}" for t in targets)
            for f, targets in sorted(broken.items())
        )
        + "\n\nEither the file moved and the comment did not, or it was "
        "never written. Update the comment, or delete the pointer -- a "
        "reader who goes looking and finds nothing learns only that the "
        "comments are not maintained."
    )


def test_start_here_catalogue_is_not_silently_incomplete():
    """The reverse direction, as a floor rather than an equality.

    Not every shipped office has to be catalogued — some are deliberate
    internals. But if the catalogue drifts far below what ships,
    students stop finding the good ones, and that failure is invisible
    because nothing is *wrong* on the page.
    """
    catalogued = _catalogue_names()
    shipped = _shipped_offices()
    uncatalogued = sorted(shipped - catalogued)
    assert len(uncatalogued) <= 4, (
        f"{len(uncatalogued)} shipped offices are missing from "
        f"START_HERE's catalogue: {uncatalogued}.\n"
        f"Add them, or raise this threshold deliberately with a note "
        f"about which ones are meant to stay unlisted."
    )


# ---------------------------------------------------------------------------
# 7. Retired vocabulary stays retired
# ---------------------------------------------------------------------------
#
# Two renames, each made because one concept had grown three names and a
# reader could not tell which one to ask a question about.
#
#   inport / outport  ->  inbox / outbox
#       The docs had already been drifting this way without deciding to:
#       course/ contained no use of "inport" at all, the recipes had
#       independently invented "mailbox", and "inbox" appeared 158 times.
#       Renaming also frees "port" for its ordinary meaning, which the
#       webhook source needs -- ``webhook(port=8000)``.
#
#   org chart  ->  network (user-facing) / graph (internals)
#       An org chart shows authority; an office shows dataflow. Org
#       charts are also trees, and an office may contain cycles, so "the
#       org chart has a loop" was incoherent.
#
# This check covers user-facing prose only. docs/internals/ and
# docs/algorithms/ still say "inport" where they are naming a real Python
# identifier (``self.inports``, ``inports_checkpointing``), which is
# correct: they document the code, and the code has not been renamed.

RETIRED_WORDS = {
    "inport": "inbox",
    "outport": "outbox",
    "org chart": "network (or 'graph' in docs/internals/)",
}

# Prose written for users, students and agents. Excludes the maintainer
# documentation that legitimately quotes code identifiers, and archive/,
# which is deliberately frozen.
_VOCABULARY_EXEMPT_PREFIXES = (
    "archive/",
    "CHANGELOG.md",
    "docs/internals/",
    "docs/algorithms/",
)


def _user_facing_markdown() -> list[Path]:
    return [
        p for p in _markdown_files()
        if not str(p.relative_to(REPO_ROOT)).startswith(
            _VOCABULARY_EXEMPT_PREFIXES
        )
    ]


def test_retired_vocabulary_does_not_return():
    offenders: dict[str, list[str]] = {}

    for path in _user_facing_markdown():
        text = path.read_text(encoding="utf-8", errors="replace").lower()
        found = [w for w in RETIRED_WORDS if w in text]
        if found:
            offenders[str(path.relative_to(REPO_ROOT))] = found

    assert not offenders, (
        "Retired vocabulary found in user-facing prose:\n"
        + "\n".join(
            f"  {f}: {', '.join(words)}"
            for f, words in sorted(offenders.items())
        )
        + "\n\nReplacements: "
        + "; ".join(f"{old} -> {new}" for old, new in RETIRED_WORDS.items())
        + "\n\nA concept with three names is a concept nobody can ask "
        "about. That is what this check exists to prevent."
    )


# ---------------------------------------------------------------------------
# 8. Link labels are plain text, never inline code
# ---------------------------------------------------------------------------
#
# ``[`course/SETUP.md`](course/SETUP.md)`` renders as a link *and* a code span at
# once. Several markdown viewers give a code span a dark background and a
# link dark blue text, and the two together are unreadable -- reported from
# the repository's own README, where the path was invisible while the same
# path without backticks, and the same backticks without a link, both read
# fine.
#
# Nothing is lost by dropping them. A path ending in .md already reads as a
# path, and the link styling already marks it as clickable. One convention
# beats two, so this holds for symbol names as well as paths.

_CODE_IN_LINK = re.compile(r"\[`[^`]*`\]\(")


def test_link_labels_are_not_inline_code():
    offenders: dict[str, int] = {}

    for path in _markdown_files():
        text = path.read_text(encoding="utf-8", errors="replace")
        hits = len(_CODE_IN_LINK.findall(text))
        if hits:
            offenders[str(path.relative_to(REPO_ROOT))] = hits

    assert not offenders, (
        "Link labels wrapped in backticks (unreadable in some viewers):\n"
        + "\n".join(f"  {f}: {n}" for f, n in sorted(offenders.items()))
        + "\n\nWrite [course/SETUP.md](course/SETUP.md), not "
        "[`course/SETUP.md`](course/SETUP.md)."
    )


# ── §9. Every diagram in the documentation is the office beside it ────────────
#
# README.md said "The diagram is generated from the office's office.md"
# for months. It was not: nothing in the repository could produce a
# diagram, and the mermaid block had been drawn by hand and copied
# forward through three documents. Nobody noticed, because a picture is
# the one part of a document a reader never checks against the code --
# they check the code against the picture.
#
# Now there is a generator, so the claim can be made true rather than
# deleted. This section is what keeps it true: wherever a document
# shows a mermaid diagram and then shows the office.md it depicts, the
# diagram must be exactly what `dsl draw` produces from that office.
#
# It compares the whole block, not just the node and edge sets. That is
# a deliberate choice and it will occasionally fail for a cosmetic
# change to the drawing. The alternative -- comparing structure and
# forgiving styling -- would let the two drift apart in every way a
# reader can see, which is the failure this section exists to prevent.
# The fix when it fails is one command, and the failure message says so.

_MERMAID_BLOCK = re.compile(r"^```mermaid\n(.*?)^```", re.M | re.S)
_PLAIN_BLOCK = re.compile(r"^```\n(.*?)^```", re.M | re.S)


def _diagram_office_pairs(text: str):
    """Each mermaid block paired with the next office.md shown after it.

    A fenced block counts as an office if it has the two sections no
    other code sample in these documents has.
    """
    for m in _MERMAID_BLOCK.finditer(text):
        for after in _PLAIN_BLOCK.finditer(text, m.end()):
            body = after.group(1)
            if "Agents:" in body and "Connections:" in body:
                yield m.group(1).rstrip("\n"), body
            break


def test_documented_diagrams_match_the_office_they_show():
    import tempfile

    from dissyslab.office.draw import draw_office_dir

    wrong: list[str] = []
    checked = 0

    for path in _markdown_files():
        text = path.read_text(encoding="utf-8", errors="replace")
        for shown, office_md in _diagram_office_pairs(text):
            checked += 1
            with tempfile.TemporaryDirectory() as tmp:
                (Path(tmp) / "office.md").write_text(office_md, encoding="utf-8")
                actual = draw_office_dir(Path(tmp))
            if shown.strip() != actual.strip():
                wrong.append(str(path.relative_to(REPO_ROOT)))

    assert checked, (
        "No diagram/office pairs found. Either the documentation stopped "
        "showing them, or the fence conventions changed and this check is "
        "now passing vacuously -- which is worse than failing."
    )
    assert not wrong, (
        "These documents show a diagram that is not the office printed "
        "beside it:\n"
        + "\n".join(f"  {f}" for f in sorted(set(wrong)))
        + "\n\nRegenerate it: `dsl draw <office_dir>` and paste the block "
        "in. A picture that disagrees with the office it claims to show "
        "is believed in preference to the office."
    )


# ── §10. An install instruction names the repository ──────────────────────────
#
# Four documents told a reader to say "Install the Python package
# dissyslab for me" and none of them said where the project lives. The
# name alone asks an assistant to trust a string it cannot check, and
# the step that follows -- installing the office-builder skill, which
# is in the repository and not on PyPI -- hands over a URL that
# appeared from nowhere.
#
# The check is narrow on purpose. It fires only on an instruction
# addressed to an assistant, which in these documents means a
# blockquote: `pip install dissyslab` in a shell block is a command a
# person runs, and it does not need provenance because they typed it
# themselves. What needs the address is the sentence a reader is told
# to say out loud to something that will act on it.

_REPO_URL = "github.com/kmchandy/DisSysLab"

# "Install `dissyslab`", "Install the Python package `dissyslab`",
# "Install its Python package `dissyslab`" -- an order to install the
# package, addressed to something that will carry it out.
#
# The backtick immediately before the name is what keeps this from
# matching prose. `pip install dissyslab` in a sentence is a command a
# person types, and its backtick sits before "pip"; "runs on any laptop
# with DisSysLab installed" is a description. Neither needs an address.
_INSTALL_ORDER = re.compile(
    r"\binstall\s+(?:the\s+|its\s+)?(?:python\s+)?(?:package\s+)?`dissyslab`",
    re.I,
)


def _quoted_install_instructions(text: str):
    """Each blockquote that orders an assistant to install the package.

    A blockquote is a run of consecutive lines starting with '>'; the
    documents use one wherever they give a reader something to say.
    Yields (first_line_number, block_text).
    """
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        if lines[i].lstrip().startswith(">"):
            start = i
            while i < len(lines) and lines[i].lstrip().startswith(">"):
                i += 1
            block = "\n".join(lines[start:i])
            # Unwrap: an instruction split over two quoted lines is one
            # sentence, and the pattern has to see it that way.
            flat = " ".join(
                ln.lstrip().lstrip(">").strip().strip("*") for ln in lines[start:i]
            )
            if _INSTALL_ORDER.search(flat):
                yield start + 1, block
        else:
            i += 1


def test_install_instructions_name_the_repository():
    offenders: list[str] = []
    checked = 0

    for path in _markdown_files():
        if path.name == "CHANGELOG.md":
            continue  # a record of what was said, not an instruction
        text = path.read_text(encoding="utf-8", errors="replace")
        for line_no, block in _quoted_install_instructions(text):
            checked += 1
            # Either source will do. The repository is the better answer
            # and the one the next step needs, but an instruction that
            # says "from PyPI" has still told the assistant where to
            # look, and a Dockerfile prompt has no use for the skill.
            if _REPO_URL not in block and "pypi" not in block.lower():
                offenders.append(f"{path.relative_to(REPO_ROOT)}:{line_no}")

    assert checked, (
        "No install instructions found at all. Either they were removed, "
        "or their shape changed and this check is now passing vacuously."
    )
    assert not offenders, (
        "These tell a reader to have an assistant install the package "
        "without saying where the project is:\n"
        + "\n".join(f"  {o}" for o in sorted(offenders))
        + f"\n\nSay where it comes from: https://{_REPO_URL} in the "
        "quoted instruction, or at minimum 'from PyPI'. A bare package "
        "name asks the assistant to trust something it cannot check, "
        "and the skill the reader needs next is in the repository "
        "rather than on PyPI, so the address has to be introduced "
        "somewhere."
    )


# ---------------------------------------------------------------------------
# 9. A skill must not name a path inside the installed package
# ---------------------------------------------------------------------------
#
# The trading skill said its office was at
# `dissyslab/gallery/apps/mac_speed_suite/`, "in the connected DisSysLab
# repo". A user who installed the wheel and ran `dsl init my_backtest`
# has no such folder -- but the assistant finds one anyway, because the
# gallery ships inside the wheel (test_wheel_contents.py asserts it, so
# that `dsl init` has something to copy). So the assistant read the
# contract correctly, wrote the new strategy into site-packages,
# reported success, and the user's own office did not have it. Nothing
# errored at any point, and `pip install -U` would have erased it.
#
# This is the eighteen-month clone assumption repeating in a second
# artifact: a path that is true in one copy of the world, written by
# someone standing in that copy. A skill should name the *kind* of
# office it works on -- an `office.md` declaring an agent `is a
# backtester` -- because a property survives copying and a path does
# not.
#
# The rule is not "never mention the package". `office-builder` sends an
# assistant to *read* the shipped example sinks there, and says in the
# same file not to edit them -- that is the correct use, and an earlier
# version of that file printed a bare relative path instead, so an agent
# ran `cat gallery/apps/...` from the student's folder and concluded the
# examples did not exist.
#
# So the invariant is: a skill that names a path inside the package must
# also say, in that file, not to write there. Naming the kind of office
# instead satisfies it by having no such path at all.

_PACKAGE_PATH_RE = re.compile(r"`[^`\n]*dissyslab/gallery/[^`\n]*`")

#: Phrases that count as saying "read here, do not write here".
_NO_WRITE_MARKERS = (
    "never repair the installation",
    "do not edit them in place",
    "never write",
    "treat it as none",
)


def _skill_prose() -> list[Path]:
    d = REPO_ROOT / "skills"
    return sorted(d.rglob("SKILL.md")) + sorted(d.rglob("references/*.md"))


@pytest.mark.parametrize(
    "skill_md", _skill_prose(), ids=lambda p: str(p.relative_to(REPO_ROOT))
)
def test_a_skill_naming_a_package_path_says_not_to_write_there(skill_md):
    text = skill_md.read_text(encoding="utf-8")
    paths = _PACKAGE_PATH_RE.findall(text)
    if not paths:
        return
    lowered = text.lower()
    assert any(m in lowered for m in _NO_WRITE_MARKERS), (
        f"{skill_md.relative_to(REPO_ROOT)} points an assistant at "
        f"{paths}, which is inside the installed package on every "
        "machine that pip-installed dissyslab -- and does not say not "
        "to write there.\n\n"
        "Anything written into the package is invisible to the user's "
        "own office and is erased by the next upgrade, with nothing "
        "erroring on the way. That is exactly what the trading skill "
        "did before it was fixed.\n\n"
        "Either name the kind of office instead -- 'a folder whose "
        "office.md declares an agent `is a backtester`' -- or say "
        "plainly in this file that the package is to be read and never "
        "written."
    )


# ---------------------------------------------------------------------------
# 10. A skill's front matter must not contain angle-bracket tokens
# ---------------------------------------------------------------------------
#
# `description: ... made by `dsl init mac_speed_suite <folder>`.` was
# rejected at save time: "SKILL.md description cannot contain XML tags".
# The skill could not be installed at all, and the only way to find out
# was to try -- the file is valid YAML, valid Markdown, and passes every
# other check here.
#
# A placeholder in angle brackets is the natural way to write a
# placeholder, which is exactly why this will happen again. The body is
# unaffected and full of them legitimately (`<office_dir>`,
# `<site-packages>`); it is the front matter that goes through the
# installer's validator.


def _front_matter(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    return m.group(1) if m else ""


@pytest.mark.parametrize(
    "skill_md",
    sorted((REPO_ROOT / "skills").glob("*/SKILL.md")),
    ids=lambda p: p.parent.name,
)
def test_skill_front_matter_has_no_angle_bracket_tokens(skill_md):
    offenders = re.findall(r"<[^>]*>", _front_matter(skill_md))
    assert not offenders, (
        f"{skill_md.parent.name}'s front matter contains {offenders}, and "
        "the installer refuses a description containing what looks like "
        "an XML tag — the skill cannot be saved at all.\n\n"
        "Use a concrete example instead of a placeholder: "
        "`dsl init mac_speed_suite my_backtest`, not "
        "`dsl init mac_speed_suite <folder>`. The body may use angle "
        "brackets freely; only the front matter is validated."
    )
