"""The package records which skill it was built with, and says so.

Skills install from the GitHub repository; the library installs from
PyPI. Two roads, so they can disagree, and a disagreement is invisible
from inside a session: the assistant reads a skill describing `dsl
checks` and draft offices, believes they exist, and every later answer
is wrong in a way the user cannot see.

The skill already refuses to describe a package older than itself. This
is the other direction — and it exists so that **nobody has to compare
`2026-08-26.a84ab36` against a string in a chat message by eye.** Asked
to do that, a beginner glances at the date and moves on, which is not
their failing; it is a job for a program.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from dissyslab.skill_versions import EXPECTED
from dissyslab.skills_installed import stale_message

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_the_recorded_versions_are_not_stale():
    """`stamp_skills.py --check` regenerates and compares. If this
    fails, someone edited a skill and did not re-stamp -- the same
    omission the content hash was introduced to catch, one level up."""
    result = subprocess.run(
        [sys.executable, "scripts/stamp_skills.py", "--check"],
        cwd=REPO_ROOT, capture_output=True, text=True,
    )
    assert result.returncode == 0, (
        "skill stamps or dissyslab/skill_versions.py are out of date:\n"
        f"{result.stdout}{result.stderr}\n"
        "Run: python scripts/stamp_skills.py"
    )


def test_every_shipped_skill_is_recorded():
    on_disk = {d.name for d in (REPO_ROOT / "skills").iterdir()
               if (d / "SKILL.md").is_file()}
    assert on_disk == set(EXPECTED), (
        "skills/ and dissyslab/skill_versions.py disagree about which "
        "skills exist"
    )


# ── the comparison itself ─────────────────────────────────────────────


def test_an_older_skill_is_reported():
    lines = stale_message("office-builder", "2020-01-01.0000000")
    assert lines, "a skill two years older than the release said nothing"
    assert "older" in " ".join(lines)
    assert "github.com" in " ".join(lines), "it must say how to fix it"


def test_the_matching_skill_is_silent():
    assert stale_message("office-builder", EXPECTED["office-builder"]) == []


def test_a_newer_skill_is_silent():
    """The false alarm that would matter most.

    Between releases the repository's skill is legitimately ahead of the
    wheel, so every student who installed the skill correctly would be
    told they had done it wrong -- and a warning that fires on the right
    behaviour is one people learn to ignore, taking the true ones with
    it.
    """
    assert stale_message("office-builder", "2099-01-01.abcdefa") == []


def test_only_the_date_is_compared():
    """Same day, different content. The hash changes several times in a
    working afternoon, and none of those are a reason to tell someone
    their install is wrong."""
    date = EXPECTED["office-builder"].split(".")[0]
    assert stale_message("office-builder", f"{date}.0000000") == []


@pytest.mark.parametrize("version", [None, "", "nonsense", "no version string"])
def test_an_unreadable_version_says_nothing(version):
    """Silence, not a guess. A skill whose version cannot be parsed is
    a skill this check knows nothing about, and inventing a verdict
    about it is how a check loses its reputation."""
    assert stale_message("office-builder", version) == []


def test_an_unknown_skill_says_nothing():
    assert stale_message("someone-elses-skill", "2020-01-01.0000000") == []
