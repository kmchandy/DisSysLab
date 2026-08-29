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
    # A save that did not take cannot carry a future date, so a newer
    # date is the one case with no ambiguity left in it.


def test_the_same_hash_is_silent_whatever_the_dates_say():
    """The false alarm that was live on 2026-08-29.

    `sensor-office-builder` was installed as `2026-08-18.935f28d` and
    the release expected `2026-08-19.935f28d` -- the same hash, so the
    same bytes, with only the hand-written date differing. The check
    compared the date and sent the user to reinstall a file that was
    already correct.

    Equal hashes mean equal content. Nothing else here is that certain,
    so it is answered first.
    """
    want_date, _, want_hash = EXPECTED["office-builder"].partition(".")
    assert stale_message("office-builder", f"2020-01-01.{want_hash}") == []
    assert stale_message("office-builder", f"2099-01-01.{want_hash}") == []


def test_the_same_day_with_different_content_is_reported():
    """The silence that was live on the same afternoon, and cost more.

    `office-builder` was installed as `2026-08-26.88b9631` while the
    release expected `2026-08-26.3caa9fc` -- different files, one
    commit apart, and the older one still told assistants the package
    required a version that did not have the commands it then named.
    Both dates read 2026-08-26, so a date comparison said nothing.

    Nothing can order two hashes, so this cannot be resolved into
    "older" or "newer"; the line names both readings. The window is
    narrow -- the skill and the release stamped on the same date -- and
    it is exactly where the failure lived.
    """
    date, _, _ = EXPECTED["office-builder"].partition(".")
    lines = stale_message("office-builder", f"{date}.0000000")
    assert lines, "same day, different content said nothing"
    joined = " ".join(lines)
    assert "newer" in joined and "did not take" in joined, (
        "it must name both readings; it cannot tell them apart"
    )
    assert "older" not in joined, "it does not know that, and must not say it"


@pytest.mark.parametrize("version", [None, "", "nonsense", "no version string"])
def test_an_unreadable_version_says_nothing(version):
    """Silence, not a guess. A skill whose version cannot be parsed is
    a skill this check knows nothing about, and inventing a verdict
    about it is how a check loses its reputation."""
    assert stale_message("office-builder", version) == []


def test_an_unknown_skill_says_nothing():
    assert stale_message("someone-elses-skill", "2020-01-01.0000000") == []
