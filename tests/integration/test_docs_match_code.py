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
    import dissyslab.gallery as gallery
    root = Path(gallery.__file__).parent
    names = set()
    for sub in ("apps", "examples"):
        d = root / sub
        if d.is_dir():
            names |= {
                c.name for c in d.iterdir() if (c / "office.md").exists()
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
