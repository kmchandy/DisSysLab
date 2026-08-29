"""`dsl doctor` is quiet when healthy and complete when not.

The failure this pins is not a crash. A first-time user asked whether
the install had worked and was told about nine dependencies, two
optional gaps and a three-agent self-test — every line true, none of it
answerable by someone who does not yet know what a sink is.

Instructing an assistant to summarise it did not work either: it
relayed the ticks, because they were on its screen and looked like the
answer. **A check in a prompt is a request; not printing it is a fact.**

So: verdict and two lines when everything is in order; the whole
inventory the moment anything is wrong, or on request.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from dissyslab.skills_installed import BASIC_SKILLS


def _install_skill(root: Path, name: str) -> Path:
    """A skill stamped exactly as this release expects.

    Not an arbitrary date: an older one now draws a "your skill predates
    this release" note, correctly, and the healthy case has to be
    genuinely healthy or it is testing the wrong thing.
    """
    from dissyslab.skill_versions import EXPECTED

    d = root / name
    d.mkdir(parents=True, exist_ok=True)
    (d / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: test\n---\n\n"
        f"**Skill version: `{EXPECTED.get(name, '2099-01-01.abcdefa')}`.**\n",
        encoding="utf-8",
    )
    return d


#: The modules `dsl doctor` reports on. Named here so the healthy
#: fixture can stand in for any that this machine happens to lack.
_DOCTOR_DEPS = ("anthropic", "dotenv", "feedparser", "requests",
                "websocket", "bs4", "PIL", "numpy", "scipy")


@pytest.fixture
def healthy_home(tmp_path, monkeypatch):
    """A machine on which nothing is wrong.

    Any of doctor's dependencies this environment does not have is
    stubbed, because otherwise these tests skip on exactly the
    machines that most need them — a CI container missing
    `websocket-client` is not evidence about the report's wording, and
    a skipped test proves nothing at all.
    """
    import sys
    import types

    for mod in _DOCTOR_DEPS:
        try:
            __import__(mod)
        except Exception:  # noqa: BLE001
            monkeypatch.setitem(sys.modules, mod, types.ModuleType(mod))

    home = tmp_path / "home"
    skills = home / ".claude" / "skills"
    for name in BASIC_SKILLS:
        _install_skill(skills, name)
    monkeypatch.setattr(Path, "home", staticmethod(lambda: home))
    monkeypatch.chdir(tmp_path)
    return home


def _doctor(capsys, argv) -> str:
    from dissyslab.cli import main

    main(argv)
    return capsys.readouterr().out


def _healthy_or_skip(out: str) -> None:
    """Skip where the machine itself is not in order.

    A container missing an optional dependency is not a bug in the
    report -- and a report that stayed terse through a genuine `[FAIL]`
    would be the actual bug, so the guard checks for the failure rather
    than for the verdict alone.
    """
    if not out.startswith("Ready") or "[FAIL]" in out:
        pytest.skip(f"environment is not healthy: {out.splitlines()[0]}")


def test_a_healthy_install_says_almost_nothing(healthy_home, capsys):
    out = _doctor(capsys, ["doctor"])
    _healthy_or_skip(out)

    assert "Dependencies:" not in out
    assert "Optional integrations" not in out
    assert "Self-test:" not in out
    assert len(out.splitlines()) <= 12, (
        "the healthy report has grown; every line here is read by "
        f"someone who asked only whether it worked:\n{out}"
    )


def test_it_still_names_the_package_and_the_skill(healthy_home, capsys):
    """The two facts the skill tells an assistant to report back, so
    the short form does not force it to go looking."""
    out = _doctor(capsys, ["doctor"])
    _healthy_or_skip(out)
    assert "dissyslab" in out
    assert "office-builder" in out


def test_it_says_how_to_see_the_rest(healthy_home, capsys):
    """Hiding detail is only acceptable if the way back is on screen."""
    out = _doctor(capsys, ["doctor"])
    _healthy_or_skip(out)
    assert "--full" in out


def test_full_prints_the_inventory(healthy_home, capsys):
    out = _doctor(capsys, ["doctor", "--full"])
    for section in ("Dependencies:", "Skills:", "Backend:", "Self-test:"):
        assert section in out, f"--full omitted {section}"


def test_a_broken_install_prints_everything_without_being_asked(
    tmp_path, monkeypatch, capsys
):
    """The half that matters more. Someone whose install is wrong did
    not ask for detail either, and cannot know to."""
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setattr(Path, "home", staticmethod(lambda: home))
    monkeypatch.chdir(tmp_path)

    out = _doctor(capsys, ["doctor"])
    assert out.startswith("Not ready")
    assert "Dependencies:" in out, (
        "a failing install must show its working, unasked -- the "
        "inventory is the diagnosis"
    )
    assert "Skills:" in out


# ── the short form's own two defects, found on 2026-08-29 ─────────────
#
# Both were in the short form only. The long form already printed "no
# version string" and already said how many copies it found; the short
# form printed a Python literal and said nothing. A summary that drops
# the finding is worse than one that is long, because the reader
# believes it.


def test_a_skill_with_no_version_line_does_not_print_the_word_None(
    healthy_home, capsys
):
    """`backtest-strategy-builder None`, on a real machine.

    A SKILL.md with no `**Skill version:**` line has ``version is
    None``, and the short form interpolated it straight into an
    f-string. A beginner asking whether their install worked was shown
    a Python literal.
    """
    d = healthy_home / ".claude" / "skills" / "office-builder"
    (d / "SKILL.md").write_text(
        "---\nname: office-builder\ndescription: test\n---\n\nNo version here.\n",
        encoding="utf-8",
    )
    out = _doctor(capsys, ["doctor"])
    _healthy_or_skip(out)
    assert " None" not in out, f"printed a Python literal at the user:\n{out}"
    assert "no version string" in out


def test_two_copies_of_one_skill_are_reported_in_the_short_form(
    healthy_home, capsys
):
    """Two installs is a finding, not a repetition.

    An assistant loads one of them and which one is not the user's to
    choose -- so the same name twice with no comment reads as a display
    glitch rather than as the thing to go and fix. The long form said
    so; the short form printed the name twice and moved on.
    """
    second = healthy_home / ".claude" / "skills" / "synced" / "abc"
    _install_skill(second, "office-builder")
    out = _doctor(capsys, ["doctor"])
    _healthy_or_skip(out)
    assert "2 copies of office-builder" in out, (
        f"the short form printed it twice and said nothing:\n{out}"
    )
