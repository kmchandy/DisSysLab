"""The catalogue cannot drift from the code that raises the codes.

A reference is believed. One that has quietly fallen behind the program
is worse than none at all -- the reader stops looking for the real
answer. So the test does not check that the catalogue is *nice*; it
reads `check_wiring.py` and checks the two sets are the same set.

This is the same shape as the `emits:` front matter and the trust
tables: adding a check forces the decision to describe it, instead of
letting the description default to absent.
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

from dissyslab.office.check_catalogue import CHECKS, catalogue_lines, get

CHECK_WIRING = Path(__file__).resolve().parents[2] / "dissyslab" / "office" / "check_wiring.py"


def _codes_raised() -> dict[str, set[str]]:
    """Every `Finding("W4", "error", ...)` in check_wiring, as code -> severities."""
    tree = ast.parse(CHECK_WIRING.read_text(encoding="utf-8"))
    found: dict[str, set[str]] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if getattr(node.func, "id", "") != "Finding":
            continue
        args = node.args
        if len(args) < 2:
            continue
        if not (isinstance(args[0], ast.Constant) and isinstance(args[1], ast.Constant)):
            continue
        found.setdefault(args[0].value, set()).add(args[1].value)
    return found


def test_every_code_the_checker_raises_has_an_entry():
    raised = set(_codes_raised())
    missing = sorted(raised - set(CHECKS))
    assert not missing, (
        f"check_wiring raises {missing} and check_catalogue does not "
        "describe them. A reader who sees that code has nowhere to go."
    )


def test_every_entry_describes_a_code_that_is_actually_raised():
    """The other direction, which is the one that rots quietly. A check
    removed from the code leaves an entry here describing behaviour the
    program no longer has."""
    extra = sorted(set(CHECKS) - set(_codes_raised()))
    assert not extra, (
        f"check_catalogue describes {extra}, which check_wiring never "
        "raises."
    )


def test_severity_agrees():
    for code, severities in _codes_raised().items():
        assert severities == {CHECKS[code].severity}, (
            f"{code} is raised as {sorted(severities)} but the catalogue "
            f"calls it {CHECKS[code].severity!r}. Whether something is a "
            "fault or a note is the first thing a reader wants."
        )


def test_there_is_no_w2():
    """Withdrawn, and deliberately not reused. The numbers are
    identifiers, not a sequence: renumbering would silently change what
    an old report meant."""
    assert "W2" not in CHECKS


# ── what a person gets ────────────────────────────────────────────────


@pytest.mark.parametrize("code", sorted(CHECKS))
def test_each_entry_says_something(code):
    check = CHECKS[code]
    assert check.title and not check.title.endswith("."), (
        "the title is a name, not a sentence"
    )
    assert len(check.meaning) > 80, f"{code}'s meaning is too short to help"


def test_lookup_is_forgiving():
    """Nobody types the case of a code they just read off a screen."""
    assert get("w11") is get("W11") is CHECKS["W11"]
    assert get(" W11 ") is CHECKS["W11"]


def test_an_unknown_code_lists_the_known_ones():
    out = "\n".join(catalogue_lines("W99"))
    assert "no check called 'W99'" in out
    assert "W11" in out, "a wrong guess should show the reader the real ones"


def test_the_notes_are_marked_in_the_list():
    """A reader scanning the table needs to know which of these mean
    'your office is wrong' before reading any of them."""
    out = "\n".join(catalogue_lines())
    for line in out.splitlines():
        if line.startswith("  W11") or line.startswith("  W12") or line.startswith("  W7 "):
            assert "*" in line
        if line.startswith("  W1 ") or line.startswith("  G2"):
            assert "*" not in line


def test_a_report_tells_you_where_to_look(tmp_path):
    """The pointer has to be in the output. A command nobody knows about
    is not an answer to 'what does W4 mean'."""
    from dissyslab.office.check_wiring import check_office_dir, format_report

    d = tmp_path / "office"
    d.mkdir()
    (d / "office.md").write_text("""# Office: x

Sources: starter
Sinks: console_printer

Agents:
A is a summarizer.

Connections:
starter's destination is A.
""", encoding="utf-8")

    text = format_report(check_office_dir(d))
    assert "dsl checks" in text
    code = text.split("dsl checks ")[1].strip()
    assert code in CHECKS, "the pointer must name a code this report used"
