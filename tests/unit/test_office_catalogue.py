"""`dsl list` is a catalogue somebody chooses from. It has to be honest.

Three failures it had, all found by installing the wheel into a clean
virtualenv and reading the output as a new user would:

1. Eight offices were described by their own wiring -- "Sources:
   starter" -- because their prose sat in `#` comment lines that the
   extractor skipped as markdown headings.
2. Ten more carried a leading `> ` into the terminal.
3. `salton_sea_dashboard` was listed under "ready to run" while
   `dsl check` reported two faults on it. The office has carried a `WIP`
   marker for months and the test sweeps honour it; `dsl list` did not
   read it.

None of these break anything. All of them are read by a beginner
deciding what to try first, which is the moment this project can least
afford to look broken.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from dissyslab.cli import _one_line_description, _unfinished_reason

REPO_ROOT = Path(__file__).resolve().parents[2]
GALLERY = REPO_ROOT / "dissyslab" / "gallery"
OFFICES = sorted(p.parent for p in GALLERY.rglob("office.md"))


def _ids(dirs):
    return [d.name for d in dirs]


@pytest.mark.parametrize("office", OFFICES, ids=_ids(OFFICES))
def test_every_shipped_office_says_what_it_is(office):
    """A blank line in the catalogue is a missing sentence someone has
    to write. There is no way to satisfy this test by suppression."""
    assert _one_line_description(office), (
        f"{office.name} has no description. Put one sentence under the "
        "title of its office.md (a `#` comment line) or its README."
    )


@pytest.mark.parametrize("office", OFFICES, ids=_ids(OFFICES))
def test_a_description_is_prose_not_wiring(office):
    """The specific wrong answer the old extractor gave."""
    text = _one_line_description(office)
    lowered = text.lower()
    assert not lowered.startswith(("sources:", "sinks:", "agents:", "connections:")), (
        f"{office.name} is described by its own wiring: {text!r}"
    )
    assert not text.startswith(">"), (
        f"{office.name} carries a markdown quote marker into the terminal: {text!r}"
    )
    assert "**" not in text, f"{office.name} carries markdown bold: {text!r}"


def test_an_unfinished_office_is_labelled_as_one():
    """`salton_sea_dashboard` is the case this exists for. If its WIP
    marker is ever removed, this test should be removed with it -- and
    that is the point: the two facts move together."""
    salton = GALLERY / "apps" / "salton_sea_dashboard"
    if not salton.is_dir():
        pytest.skip("office has been removed from the gallery")
    reason = _unfinished_reason(salton)
    assert reason, "the WIP marker is gone but the office is still shipped"
    assert "not registered" in reason or len(reason) > 10, (
        "the marker should say what is missing, not just that something is"
    )


@pytest.mark.parametrize("office", OFFICES, ids=_ids(OFFICES))
def test_a_finished_office_is_not_labelled_unfinished(office):
    """The other direction. A marker left behind after the work is done
    is how a working office ends up advertised as broken."""
    if office.name == "salton_sea_dashboard":
        return
    assert not _unfinished_reason(office), (
        f"{office.name} carries a WIP marker. Either it is unfinished -- "
        "in which case say so here -- or the marker should come out."
    )


def test_the_listing_marks_it(capsys):
    """End to end, because the two helpers being right does not mean the
    line a person reads is right."""
    from dissyslab.cli import main

    main(["list"])
    out = capsys.readouterr().out
    for line in out.splitlines():
        if "salton_sea_dashboard" in line:
            assert "(unfinished)" in line
            break
    else:
        pytest.skip("office not present in this install")


def test_no_persona_names_in_the_catalogue(capsys):
    """`Pat` and `Builders` are who this project designs for. A student
    reading `dsl list` has never met them, and a heading naming someone
    they cannot ask about is the same defect as an unexplained `W11`.

    Whole words only. `Susan` and `Vikram` are agent names inside
    example offices, which is a different thing entirely -- a substring
    match here would have failed on `Susan scores each article`.
    """
    import re

    from dissyslab.cli import main

    main(["list"])
    out = capsys.readouterr().out
    for name in ("Pat", "Builders"):
        assert not re.search(rf"\b{name}\b", out), (
            f"{name} is a persona from this project's own documents, "
            "not something a user of the catalogue knows"
        )
