"""Finding the skills an assistant would actually load.

The step this replaces was: *"ask your assistant which version of the
office-builder skill it has."* That asks the possibly-unreliable thing
whether it is reliable. An assistant that never loaded the skill still
answers, and answers plausibly, and then improvises its own
concurrency — which is the failure the skill exists to prevent, and the
one self-report structurally cannot detect.

Where a skill lives is a filesystem question, so these tests are about
the filesystem.
"""
from __future__ import annotations

from pathlib import Path

import subprocess
import sys

from dissyslab.skills_installed import (
    BASIC_SKILLS,
    CATALOGUE,
    DISSYSLAB_SKILLS,
    DOMAIN_SKILLS,
    catalogue_lines,
    find_installed,
    report_lines,
    search_roots,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
SKILL_SRC = REPO_ROOT / "skills"


def _install(root: Path, name: str, version: str = "2026-08-19.385377d") -> Path:
    """A minimal skill of the open format: a directory with SKILL.md."""
    d = root / name
    d.mkdir(parents=True)
    (d / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: test\n---\n\n"
        f"**Skill version: `{version}`.**\n",
        encoding="utf-8",
    )
    return d


def test_finds_a_skill_in_a_project_directory(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path / "home"))
    (tmp_path / "home").mkdir()
    _install(tmp_path / "proj" / ".claude" / "skills", "office-builder")

    found, _roots = find_installed(cwd=tmp_path / "proj")
    assert [(s.name, s.version) for s in found] == [
        ("office-builder", "2026-08-19.385377d")
    ]


def test_reads_the_codex_directory_too(tmp_path, monkeypatch):
    """Skills are an open format; only the directories differ. Codex
    reads `.agents/skills`, and a user on Codex must get the same
    answer as a user on Claude."""
    monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path / "home"))
    _install(tmp_path / "home" / ".agents" / "skills", "office-builder")

    found, _roots = find_installed(cwd=tmp_path / "elsewhere")
    assert [s.name for s in found] == ["office-builder"]


def test_someone_elses_skill_is_not_ours(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path / "home"))
    _install(tmp_path / "home" / ".claude" / "skills", "pdf")

    found, _roots = find_installed(cwd=tmp_path)
    assert found == []


def test_a_missing_skill_says_what_it_costs(tmp_path, monkeypatch):
    """"not installed" is a fact. The consequence is the part a
    beginner cannot infer, and it is the whole reason for the check."""
    monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path / "home"))
    (tmp_path / "home").mkdir()

    text = "\n".join(report_lines(cwd=tmp_path))
    assert "office-builder: not installed" in text
    assert "improvise its" in text
    assert "github.com/kmchandy/DisSysLab" in text


def test_two_copies_are_reported_as_two(tmp_path, monkeypatch):
    """An assistant loads one of them and which one is not the user's
    choice. Silently reporting "installed" would hide a stale copy,
    which is the exact bug the version string was added for."""
    monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path / "home"))
    _install(tmp_path / "home" / ".claude" / "skills", "office-builder",
             "2026-01-01.aaaaaaa")
    _install(tmp_path / "proj" / ".claude" / "skills", "office-builder",
             "2026-08-19.385377d")

    text = "\n".join(report_lines(cwd=tmp_path / "proj"))
    assert "2026-01-01.aaaaaaa" in text
    assert "2026-08-19.385377d" in text
    assert "2 copies" in text


def test_a_skill_bundled_in_a_plugin_is_found(tmp_path, monkeypatch):
    """Claude plugins, Codex plugins and Gemini extensions all carry
    skills in a `skills/` subdirectory. The bundle's own name is the
    author's choice, so the roots are globbed."""
    monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path / "home"))
    _install(
        tmp_path / "home" / ".claude" / "plugins" / "dissyslab" / "skills",
        "office-builder",
    )
    found, _roots = find_installed(cwd=tmp_path)
    assert [s.name for s in found] == ["office-builder"]


def test_the_roots_searched_are_always_reported(tmp_path, monkeypatch):
    """A skill installed somewhere this module has never heard of would
    otherwise read as "not installed" — the same silent wrong answer
    this check exists to prevent, one level up. Printing the list makes
    it a question the user can answer."""
    monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path / "home"))
    (tmp_path / "home").mkdir()
    text = "\n".join(report_lines(cwd=tmp_path))
    assert "searched:" in text
    assert ".claude/skills" in text
    assert ".agents/skills" in text


def test_a_skill_with_no_version_string_still_reports(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path / "home"))
    d = tmp_path / "home" / ".claude" / "skills" / "office-builder"
    d.mkdir(parents=True)
    (d / "SKILL.md").write_text("---\nname: office-builder\n---\nno version\n")

    text = "\n".join(report_lines(cwd=tmp_path))
    assert "no version string" in text


def test_search_roots_never_raises_without_a_home(monkeypatch):
    """doctor must always finish. A odd environment is not a reason to
    fail the one command people run when something is already wrong."""
    assert search_roots() == search_roots()
    assert all(isinstance(r, Path) for r in search_roots())


# ── basic skills are required; domain skills are not ──────────────────


def test_a_missing_domain_skill_is_not_reported_as_missing(tmp_path, monkeypatch):
    """Su installs office-builder and nothing else, and her doctor
    output must not accuse her of missing a trading skill. A report
    that lists every optional thing you have not got is a report
    people stop reading, and the one line that mattered goes with it.
    """
    monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path / "home"))
    _install(tmp_path / "home" / ".claude" / "skills", "office-builder")

    text = "\n".join(report_lines(cwd=tmp_path))
    for name in DOMAIN_SKILLS:
        assert name not in text, (
            f"doctor mentions {name}, which is not installed and was "
            "never asked for."
        )


def test_a_missing_basic_skill_is_still_reported(tmp_path, monkeypatch):
    """The other half of the same rule. Silence about domain skills
    must not become silence about the ones that matter."""
    monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path / "home"))
    (tmp_path / "home").mkdir()

    text = "\n".join(report_lines(cwd=tmp_path))
    for name in BASIC_SKILLS:
        assert f"{name}: not installed" in text


def test_an_installed_domain_skill_is_reported(tmp_path, monkeypatch):
    """Absence is silent; presence is not. Vikram needs to see which
    version of the trading skill is loaded for the same reason Su needs
    to see office-builder's — an install can report success while the
    old copy stays resident."""
    monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path / "home"))
    _install(
        tmp_path / "home" / ".claude" / "skills",
        "backtest-strategy-builder",
        version="2026-08-25.d01444c",
    )

    text = "\n".join(report_lines(cwd=tmp_path))
    assert "[OK] backtest-strategy-builder 2026-08-25.d01444c" in text


def test_every_shipped_skill_is_classified():
    """A skill added to skills/ and to DISSYSLAB_SKILLS but to neither
    BASIC_SKILLS nor DOMAIN_SKILLS would be looked for and then never
    reported either way."""
    assert set(DISSYSLAB_SKILLS) == set(BASIC_SKILLS) | set(DOMAIN_SKILLS)
    assert not (set(BASIC_SKILLS) & set(DOMAIN_SKILLS))


def test_the_shipped_skills_are_the_ones_we_look_for():
    """If a skill is added to skills/ and not to DISSYSLAB_SKILLS,
    `dsl doctor` will report it as absent on a machine where it is
    installed."""
    on_disk = {p.name for p in SKILL_SRC.iterdir() if (p / "SKILL.md").is_file()}
    assert on_disk == set(DISSYSLAB_SKILLS), (
        f"skills/ holds {sorted(on_disk)} but doctor looks for "
        f"{sorted(DISSYSLAB_SKILLS)}."
    )


# ── `dsl skills`: what is there, as against what is installed ─────────
#
# `dsl doctor` answers "is what I need installed?". This answers "what
# is there?", and it is the only thing that can: an assistant matches
# your words against a skill's `description:`, and a skill that is not
# installed has no description on this machine. So an assistant cannot
# tell you about a skill you do not already have, and will answer
# anyway.


def test_the_catalogue_names_every_shipped_skill():
    """The listing is hardcoded in the package because it has to name
    skills that are *not* installed, whose SKILL.md is therefore
    absent. That makes it a second place the truth lives, so pin it."""
    on_disk = {p.name for p in SKILL_SRC.iterdir() if (p / "SKILL.md").is_file()}
    assert {s.name for s in CATALOGUE} == on_disk


def test_every_catalogue_entry_says_what_the_skill_lets_you_do():
    for entry in CATALOGUE:
        assert entry.blurb.strip(), f"{entry.name} has no blurb"
        assert entry.kind in ("basic", "domain")


def test_an_uninstalled_skill_is_listed_with_how_to_get_it(tmp_path, monkeypatch):
    """The case the command exists for. Absence here is not a fault to
    report -- it is the thing being answered."""
    monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path / "home"))
    (tmp_path / "home").mkdir()

    text = "\n".join(catalogue_lines(cwd=tmp_path))
    for entry in CATALOGUE:
        assert entry.name in text
    assert "not installed" in text
    assert "github.com/kmchandy/DisSysLab" in text


def test_an_installed_skill_is_marked_with_its_version(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path / "home"))
    _install(tmp_path / "home" / ".claude" / "skills", "office-builder")

    text = "\n".join(catalogue_lines(cwd=tmp_path))
    assert "[OK] office-builder  2026-08-19.385377d" in text


def test_it_says_where_it_looked(tmp_path, monkeypatch):
    """Same reason `dsl doctor` does. A skill installed somewhere this
    module has never heard of otherwise reads as 'not installed',
    which is the silent wrong answer one level up."""
    monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path / "home"))
    (tmp_path / "home").mkdir()
    assert "searched:" in "\n".join(catalogue_lines(cwd=tmp_path))


def test_dsl_skills_runs():
    out = subprocess.run(
        [sys.executable, "-m", "dissyslab.cli", "skills"],
        capture_output=True, text=True, cwd=REPO_ROOT,
    )
    assert out.returncode == 0
    assert "office-builder" in out.stdout
    assert "backtest-strategy-builder" in out.stdout


def test_office_builder_names_every_other_shipped_skill():
    """`office-builder` is the only skill guaranteed to be installed, so
    it is the only one that can mention a skill the user does not have.
    An assistant matches words against a skill's `description:`, and an
    uninstalled skill has none on this machine — so without this index
    a domain skill is invisible to the person it was written for.

    Which makes the index a second place the truth lives. Pin it.
    """
    text = (SKILL_SRC / "office-builder" / "SKILL.md").read_text(encoding="utf-8")
    for entry in CATALOGUE:
        if entry.name == "office-builder":
            continue
        assert entry.name in text, (
            f"{entry.name} ships but office-builder never mentions it, "
            "so an assistant without it will not know it exists."
        )
    assert "dsl skills" in text, (
        "office-builder should point at `dsl skills` — the listing is "
        "the part that stays true as skills are added."
    )
