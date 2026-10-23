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
    # The backend decides which key the report names. A shell left on
    # DSL_BACKEND=openrouter (Lab 2's trials) made the key line say
    # OPENROUTER_API_KEY; every test here assumes the default backend.
    monkeypatch.delenv("DSL_BACKEND", raising=False)

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


def test_it_names_the_package_and_the_key_but_no_skill(healthy_home, capsys, monkeypatch):
    """The short form is for a student asking whether it works. Skills
    are about assistants; `this is not the copy this release was built
    with` about a skill they never installed reads as a fault."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    out = _doctor(capsys, ["doctor"])
    _healthy_or_skip(out)
    assert out.splitlines()[:2] == ["Ready. You can build an office.",
                                    "  Key: ANTHROPIC_API_KEY is set."]
    assert "dissyslab" in out
    assert "office-builder" not in out and "Skills:" not in out


def test_a_missing_key_is_said_under_the_verdict(healthy_home, capsys, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("DSL_BACKEND", raising=False)
    out = _doctor(capsys, ["doctor"])
    _healthy_or_skip(out)
    assert out.splitlines()[1] == ("  Key: ANTHROPIC_API_KEY is not set. "
                                   "Offices with LLM agents need it;")


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

    import dissyslab.cli as cli

    monkeypatch.setattr(cli, "_smoke_test_office", lambda: [])
    out = _doctor(capsys, ["doctor"])
    assert out.startswith("Not ready")
    assert "Dependencies:" in out, (
        "a failing install must show its working, unasked -- the "
        "inventory is the diagnosis"
    )
    assert "Skills:" in out


# The short form used to list the installed skills, and two defects were
# found in that listing on 2026-08-29 (a Python `None` for a skill with no
# version line; two copies printed with no comment). The short form no
# longer lists skills at all (19 Oct 2026); the long form's handling of
# both is tested in test_skills_installed.py.


# ── `dsl doctor <office>`: will this office run here? ──────────────────

GALLERY = Path(__file__).resolve().parents[2] / "dissyslab" / "gallery"


def _office_section(capsys, office: Path) -> tuple[int, list[str]]:
    from dissyslab.cli import main

    code = main(["doctor", str(office)])
    out = capsys.readouterr().out.splitlines()
    first = next(i for i, ln in enumerate(out) if ln.startswith("This office, "))
    last = next(i for i in range(first, len(out)) if out[i].endswith("to run.")
                or out[i].startswith("Not ready to run:"))
    return code, out[first:last + 1]


def _copy(name: str, tmp_path: Path) -> Path:
    import shutil

    dst = tmp_path / name
    shutil.copytree(GALLERY / name, dst, ignore=shutil.ignore_patterns("__pycache__"))
    return dst


def test_an_office_with_llm_agents_and_no_key_is_not_ready_to_run(
    healthy_home, capsys, monkeypatch, tmp_path
):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("DSL_BACKEND", raising=False)
    code, lines = _office_section(capsys, _copy("incident_room", tmp_path))
    assert lines == [
        "This office, incident_room:",
        "  [OK] dsl check: no problems",
        "  [FAIL] ANTHROPIC_API_KEY is not set, and these are LLM agents: Lena, Max, Rae, Wren",
        "  [OK] evidence.jsonl: there (read by evidence)",
        "",
        "Not ready to run: ANTHROPIC_API_KEY is not set.",
    ]
    assert code == 1


def test_with_the_key_it_is_ready_to_run(healthy_home, capsys, monkeypatch, tmp_path):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    monkeypatch.delenv("DSL_BACKEND", raising=False)
    code, lines = _office_section(capsys, _copy("incident_room", tmp_path))
    assert lines[2] == ("  [OK] ANTHROPIC_API_KEY is set; the LLM agents need it: "
                        "Lena, Max, Rae, Wren")
    assert lines[-1] == "Ready to run."


def test_an_office_of_python_agents_needs_no_key(healthy_home, capsys, monkeypatch, tmp_path):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("DSL_BACKEND", raising=False)
    _code, lines = _office_section(capsys, _copy("returns_desk", tmp_path))
    assert "  [OK] no LLM agents: no key needed" in lines
    assert lines[-1] == "Ready to run."


def test_a_missing_source_file_is_named(healthy_home, capsys, monkeypatch, tmp_path):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    office = _copy("incident_room", tmp_path)
    (office / "evidence.jsonl").unlink()
    code, lines = _office_section(capsys, office)
    assert "  [FAIL] evidence.jsonl: not there (read by evidence)" in lines
    assert lines[-1] == "Not ready to run: evidence.jsonl is missing."
    assert code == 1


def test_a_folder_that_is_not_an_office_says_so(healthy_home, capsys, tmp_path):
    code, lines = _office_section(capsys, tmp_path)
    assert lines[-1] == f"Not ready to run: {tmp_path} is not an office folder."
    assert code == 1
