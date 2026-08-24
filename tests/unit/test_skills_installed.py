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

from dissyslab.skills_installed import (
    DISSYSLAB_SKILLS,
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


def test_the_shipped_skills_are_the_ones_we_look_for():
    """If a skill is added to skills/ and not to DISSYSLAB_SKILLS,
    `dsl doctor` will report it as absent on a machine where it is
    installed."""
    on_disk = {p.name for p in SKILL_SRC.iterdir() if (p / "SKILL.md").is_file()}
    assert on_disk == set(DISSYSLAB_SKILLS), (
        f"skills/ holds {sorted(on_disk)} but doctor looks for "
        f"{sorted(DISSYSLAB_SKILLS)}."
    )
