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
    deep_search,
    find_installed,
    is_source_checkout,
    locate,
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
    assert "office-builder: not found" in text
    assert "improvise its own" in text
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
        assert f"{name}: not found" in text


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
    assert "not found" in text
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


# ── when the known places are wrong ───────────────────────────────────
#
# On 2026-08-26 `dsl doctor` told this project's author that
# office-builder was not installed while he was using it. Cowork
# materialises account skills under
# ~/Library/Application Support/Claude/local-agent-mode-sessions/
# skills-plugin/<uuid>/<uuid>/skills/, two UUID levels down, in a
# directory named for a *session*. No list of known places could have
# had that in it, and the next rename will break the list again.
#
# So the fast search stays, and a home-wide walk backs it up.


def test_a_skill_in_the_desktop_apps_own_directory_is_found(tmp_path, monkeypatch):
    """The exact layout that was reported as missing."""
    monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path / "home"))
    _install(
        tmp_path / "home" / "Library" / "Application Support" / "Claude"
        / "local-agent-mode-sessions" / "skills-plugin"
        / "e96bd284-583e-4f55-a626-f0437a8bd087"
        / "8a9e7d88-e0db-49d8-a6a4-72eb31384cbf" / "skills",
        "office-builder",
    )
    found, _roots = find_installed(cwd=tmp_path)
    assert [s.name for s in found] == ["office-builder"]


def test_the_deep_search_finds_a_skill_nobody_predicted(tmp_path, monkeypatch):
    """The point of the walk: it knows nothing about anyone's layout,
    so it keeps working when a vendor moves something."""
    monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path / "home"))
    _install(
        tmp_path / "home" / "somewhere" / "nobody" / "guessed" / "skills",
        "office-builder",
    )
    fast, _roots = find_installed(cwd=tmp_path)
    assert fast == []
    assert [s.name for s in deep_search()] == ["office-builder"]


def test_the_walk_happens_by_itself_when_a_basic_skill_is_missing(
    tmp_path, monkeypatch
):
    """Su is twelve, she did what she was told, and "not installed —
    go install it" is a wall. She should not have to know a second
    command exists, so the fallback is automatic rather than offered."""
    monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path / "home"))
    _install(
        tmp_path / "home" / "unexpected" / "place" / "skills", "office-builder"
    )
    found, _roots, went_deep = locate(cwd=tmp_path)
    assert went_deep
    assert "office-builder" in {s.name for s in found}


def test_the_walk_is_skipped_when_the_fast_search_succeeds(tmp_path, monkeypatch):
    """The slow path costs nothing to anyone whose skills are where we
    expected, which is what makes it affordable as a default."""
    monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path / "home"))
    for name in BASIC_SKILLS:
        _install(tmp_path / "home" / ".claude" / "skills", name)
    _found, _roots, went_deep = locate(cwd=tmp_path)
    assert not went_deep


def test_the_walk_does_not_enter_a_node_modules_tree(tmp_path, monkeypatch):
    """Not correctness — a skill could be in there. But a search people
    abandon finds nothing, and "slower" must not become "hangs"."""
    monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path / "home"))
    _install(
        tmp_path / "home" / "proj" / "node_modules" / "x" / "skills",
        "office-builder",
    )
    assert deep_search() == []


def test_the_repository_copy_is_not_an_installed_skill(tmp_path, monkeypatch):
    """A home-wide walk finds the project's own `skills/` folder. That
    is the *source* of a skill, not an installed one — an assistant
    loads what the vendor materialised, and calling a clone "installed"
    is how someone concludes an install took when it did not."""
    monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path / "home"))
    checkout = tmp_path / "home" / "DisSysLab"
    (checkout / "skills").mkdir(parents=True)
    (checkout / "pyproject.toml").write_text("[project]\nname='dissyslab'\n")
    d = _install(checkout / "skills", "office-builder")

    assert is_source_checkout(d)
    text = "\n".join(report_lines(cwd=tmp_path))
    assert "repository's own copy" in text
    assert "[OK] office-builder" not in text


def test_the_verdict_says_not_ready_when_the_skill_is_missing(tmp_path, monkeypatch):
    """The line that must survive being summarised. It used to be one
    `[    ]` among nine ticks, and an assistant reading the output told
    a twelve-year-old everything was fine."""
    from dissyslab.cli import _doctor_verdict

    monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path / "home"))
    (tmp_path / "home").mkdir()
    verdict, detail, _smoke = _doctor_verdict()
    assert verdict.startswith("Not ready")
    assert "office-builder" in verdict
    assert any("improvise" in line for line in detail)

    # And it must not claim the skill is *not installed*. Doctor
    # searched some folders and found nothing in them; what exists on
    # this disk is not something it knows. This is the same wording
    # mistake the Skills section was rewritten to stop making, and it
    # survived in the verdict line for a fortnight because nothing
    # tested the sentence a reader actually reads first.
    assert "not installed" not in verdict
    assert any("looked" in line for line in detail), (
        "when it found nothing, the verdict must offer where it looked"
    )


def test_found_only_in_a_clone_is_a_different_verdict(tmp_path, monkeypatch):
    """Two situations, two sentences. "I could not find it" is a
    statement about doctor's search; "it is in the repository but not
    installed" is a statement about a folder it actually read. The
    second is more useful precisely because it is a stronger claim, and
    it is only sayable when true."""
    from dissyslab.cli import _doctor_verdict

    home = tmp_path / "home"
    monkeypatch.setattr(Path, "home", staticmethod(lambda: home))
    checkout = home / "DisSysLab"
    (checkout / "skills").mkdir(parents=True)
    (checkout / "pyproject.toml").write_text("[project]\nname='dissyslab'\n")
    for name in BASIC_SKILLS:
        _install(checkout / "skills", name)
    monkeypatch.chdir(tmp_path)

    verdict, detail, _smoke = _doctor_verdict()
    assert verdict.startswith("Not ready")
    assert "repository" in verdict
    assert any("clone" in line for line in detail)


def test_a_missing_api_key_is_not_a_reason_to_say_not_ready(tmp_path, monkeypatch):
    """Offices whose roles are all Python need no credential, and those
    are the ones a new user runs first. A verdict that cried wolf about
    a key would teach people to skip the verdict."""
    from dissyslab.cli import _doctor_verdict

    monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path / "home"))
    for name in BASIC_SKILLS:
        _install(tmp_path / "home" / ".claude" / "skills", name)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.chdir(tmp_path)

    verdict, _detail, _smoke = _doctor_verdict()
    assert verdict.startswith("Ready")


# ── the synced layout ─────────────────────────────────────────────────


def test_a_synced_account_skill_is_found(tmp_path, monkeypatch):
    """The layout that broke it, reported from a real session.

    Claude syncs account skills to
    `~/.claude/skills/synced/<uuid>/office-builder/SKILL.md` -- two
    levels below `skills`. Both the fast path and `deep_search` walked
    past, because the walk also required the *parent* directory to be
    named `skills`.

    The consequence was worse than a wrong answer. Doctor said the
    skill was missing and told the user to install it from GitHub;
    installing it changed nothing, because it was already there, and
    doctor said the same thing again. A loop with no way out.
    """
    home = tmp_path / "home"
    synced = home / ".claude" / "skills" / "synced" / "abc-123" / "office-builder"
    synced.mkdir(parents=True)
    (synced / "SKILL.md").write_text(
        "---\nname: office-builder\ndescription: d\n---\n\n"
        "**Skill version: `2026-01-01.abc1234`.**\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(Path, "home", staticmethod(lambda: home))

    assert [s.name for s in deep_search(home)] == ["office-builder"]

    found, _roots, _deep = locate(cwd=tmp_path)
    assert [s.name for s in found] == ["office-builder"], (
        "the fast path must find it too, or every session pays for a "
        "home-wide walk"
    )


def test_a_skill_is_found_wherever_it_is(tmp_path, monkeypatch):
    """The general rule that replaced the guess. A skill is a directory
    named after one of ours holding SKILL.md -- under any parent, at
    any depth. Requiring a `skills` parent was the same class of
    mistake as the fast path's list of known directories: an assumption
    about somebody else's product, correct until they move it."""
    home = tmp_path / "home"
    odd = home / "Library" / "whatever" / "v3" / "bundle" / "office-builder"
    odd.mkdir(parents=True)
    (odd / "SKILL.md").write_text(
        "---\nname: office-builder\ndescription: d\n---\n", encoding="utf-8"
    )
    monkeypatch.setattr(Path, "home", staticmethod(lambda: home))
    assert [s.name for s in deep_search(home)] == ["office-builder"]


def test_a_directory_that_is_not_ours_is_ignored(tmp_path, monkeypatch):
    """Dropping the `skills` parent rule widened the net; it must not
    have widened it to everyone else's skills."""
    home = tmp_path / "home"
    other = home / ".claude" / "skills" / "synced" / "x" / "someone-elses-skill"
    other.mkdir(parents=True)
    (other / "SKILL.md").write_text(
        "---\nname: someone-elses-skill\ndescription: d\n---\n", encoding="utf-8"
    )
    monkeypatch.setattr(Path, "home", staticmethod(lambda: home))
    assert deep_search(home) == []
