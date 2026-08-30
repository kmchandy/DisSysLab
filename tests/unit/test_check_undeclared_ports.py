"""The three holes on the far side of "a role declares its ports".

W1, W2, W13 and W14 are one idea counted four ways. Take the set of
inboxes an agent declares and the set that connections write to, and
compare them both directions; do the same for outboxes:

    W1   declared inbox   - wired      an agent that will block
    W13  wired inbox      - declared   a message that reaches nothing
    W2   declared outbox  - wired      a send that will raise
    W14  wired outbox     - declared   a connection nothing travels

Three of those four existed. Each test here was written after finding
its fault by hand, on a shipped office, while checking that a slide in
the micro-course was telling the truth -- which is a slow way to find
things and the reason they are pinned now.

**W15 is the one underneath all of them.** Every check above reads a
declaration, so a role that declares nothing makes all four stand down.
The office then reported `no problems`, and the reader has no way to
tell that from `your ports are fine`. `dsl build` refused the same file
four commands later. A check whose silence has two meanings is worse
than no check, because the reader stops looking.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from dissyslab.office.check_wiring import check_office_dir

REPO_ROOT = Path(__file__).resolve().parents[2]
GALLERY = REPO_ROOT / "dissyslab" / "gallery"

_NEW = {"W13", "W14", "W15"}


def _office(tmp_path, office_md: str, roles: dict[str, str] | None = None):
    d = tmp_path / "office"
    (d / "roles").mkdir(parents=True, exist_ok=True)
    (d / "office.md").write_text(office_md, encoding="utf-8")
    for name, body in (roles or {}).items():
        (d / "roles" / name).write_text(body, encoding="utf-8")
    return d


def _codes(report):
    return [f.code for f in report.findings]


def _of(report, code):
    return [f for f in report.findings if f.code == code]


_ANALYST = """---
emits: one sentence about the story
outboxes: briefing
adds: text
---
# Role: analyst

Write one sentence about each story. Send to briefing.
"""

_FILTER = """---
emits: whether to keep the item
outboxes: keep, discard
---
# Role: my_filter

If the item is relevant, send to keep. Otherwise send to discard.
"""

_ONE_AGENT = """# Office: x

Sources: starter
Sinks: console_printer

Agents:
Alex is an analyst.

Connections:
starter's destination is Alex.
Alex's {outbox} is console_printer{inbox}.
"""


# ── W15: a role file that will not say ────────────────────────────────


def test_a_role_that_declares_nothing_is_reported(tmp_path):
    """The fixture is the mistake a beginner makes on their first role:
    they write the prose and not the four lines above it."""
    d = _office(
        tmp_path,
        _ONE_AGENT.format(outbox="briefing", inbox=""),
        {"analyst.md": "# Role: analyst\n\nWrite one sentence. Send to briefing.\n"},
    )
    report = check_office_dir(d)
    assert "W15" in _codes(report), (
        "a role file with no front matter checked clean; the office cannot "
        "be built and the check said nothing"
    )
    assert not report.ok


def test_the_report_names_the_file_and_says_what_to_add(tmp_path):
    """`analyst.md does not say...` -- the file, not the agent, because
    the file is what the reader has to open. And the remedy is the
    front matter itself, so it can be copied."""
    d = _office(
        tmp_path,
        _ONE_AGENT.format(outbox="briefing", inbox=""),
        {"analyst.md": "# Role: analyst\n\nSend to briefing.\n"},
    )
    finding = _of(check_office_dir(d), "W15")[0]
    assert "analyst.md" in finding.message
    assert "outboxes:" in finding.hint


def test_the_port_checks_stand_down_which_is_why_W15_exists(tmp_path):
    """The office below has *two* faults on top of the missing
    declaration -- an outbox that does not exist and an inbox that does
    not exist. Neither can be seen. This test exists to record why the
    silence was dangerous rather than merely incomplete."""
    d = _office(
        tmp_path,
        _ONE_AGENT.format(outbox="summary", inbox="'s nope"),
        {"analyst.md": "# Role: analyst\n\nSend to briefing.\n"},
    )
    codes = _codes(check_office_dir(d))
    assert "W15" in codes
    assert "W14" not in codes, "W14 cannot fire without a declaration to read"
    assert "W1" not in codes and "W2" not in codes


def test_a_role_built_by_a_factory_is_still_silent(tmp_path):
    """The distinction W15 turns on: *unknown* stays quiet, *undeclared*
    does not. A synchronizer has no file to read, and reporting it would
    make the check fire on offices that are entirely correct."""
    d = _office(tmp_path, """# Office: x

Sources: starter
Sinks: console_printer

Agents:
Sync is a synchronizer(inboxes=["a", "b"]).

Connections:
starter's destination is Sync's a.
starter's destination is Sync's b.
Sync's out is console_printer.
""")
    assert "W15" not in _codes(check_office_dir(d))


# ── W13 at the sink end ───────────────────────────────────────────────


def test_a_sink_inbox_that_does_not_exist_is_reported(tmp_path):
    """A sink has exactly one inbox, `in_`, and it is never named. The
    agents loop cannot see this: a sink is not an agent and declares
    nothing. So this compiled into run.py and died at run time inside
    network.py -- a framework traceback, about a port the student typed,
    from the command the check runs before."""
    d = _office(
        tmp_path,
        _ONE_AGENT.format(outbox="briefing", inbox="'s nope"),
        {"analyst.md": _ANALYST},
    )
    findings = _of(check_office_dir(d), "W13")
    assert findings, "a message addressed to a sink inbox that does not exist"
    assert "nope" in findings[0].message
    assert "console_printer" in findings[0].hint, (
        "the hint must be the corrected sentence, not advice"
    )


def test_the_default_sink_inbox_is_not_a_fault(tmp_path):
    """`in_` written out is unusual but legal. Firing on it would be a
    false positive on anyone who read the grammar too carefully."""
    for spelling in ("", "'s in_"):
        d = _office(
            tmp_path / spelling.replace("'", "").replace(" ", "_"),
            _ONE_AGENT.format(outbox="briefing", inbox=spelling),
            {"analyst.md": _ANALYST},
        )
        assert "W13" not in _codes(check_office_dir(d)), spelling


# ── W14: sending from an outbox that does not exist ───────────────────


def test_a_misspelled_outbox_names_the_word_the_student_typed(tmp_path):
    """The fault this fixes is misdirection, not silence.

    `Alex's summary is ...` left the real outbox `briefing` wired to
    nothing *by construction*, so the office reported W2 about
    `briefing` -- the name spelled correctly -- and never mentioned
    `summary`. The reader was told to wire or delete a port they had not
    touched, and their actual typo was not in the report.
    """
    d = _office(
        tmp_path,
        _ONE_AGENT.format(outbox="summary", inbox=""),
        {"analyst.md": _ANALYST},
    )
    report = check_office_dir(d)
    w14 = _of(report, "W14")
    assert w14, "the misspelled outbox was not reported"
    assert "summary" in w14[0].message, "the report must name what was typed"
    assert "briefing" in w14[0].hint, "and what it should have been"
    assert "W2" not in _codes(report), (
        "W2 on the correctly-spelled outbox is the same typo said twice, "
        "and it is the half that points away from the mistake"
    )


def test_W2_still_fires_when_an_outbox_is_simply_unwired(tmp_path):
    """The other side of that stand-down. A filter wired only on `keep`
    is the case W2 was built for, and W14 must not swallow it."""
    d = _office(tmp_path, """# Office: x

Sources: starter
Sinks: console_printer

Agents:
Screen is a my_filter.

Connections:
starter's destination is Screen.
Screen's keep is console_printer.
""", {"my_filter.md": _FILTER})
    codes = _codes(check_office_dir(d))
    assert "W2" in codes, "an unwired `discard` is still a fault"
    assert "W14" not in codes


def test_a_single_outbox_role_may_be_wired_through_out(tmp_path):
    """A generator normalises a single outbox to `out` at build time and
    several shipped offices are wired against that name. Both spellings
    reach the same port. Removing this allowance is what would make W14
    fire on the gallery."""
    d = _office(
        tmp_path,
        _ONE_AGENT.format(outbox="out", inbox=""),
        {"analyst.md": _ANALYST},
    )
    assert "W14" not in _codes(check_office_dir(d))


# ── the measurement ───────────────────────────────────────────────────


def _shipped_offices():
    seen = set()
    for pattern in ("*/office.md", "*/*/office.md"):
        for root in ("apps", "examples"):
            for path in sorted((GALLERY / root).glob(pattern)):
                seen.add(path.parent)
    return sorted(seen)


@pytest.mark.parametrize(
    "office", _shipped_offices(), ids=lambda p: p.name
)
def test_the_new_checks_are_silent_on_every_shipped_office(office):
    """A new check earns its place by finding a real fault and by being
    quiet everywhere else. This is the second half, and it is the half
    that fails when someone tightens a rule without measuring: forty
    offices, none of which should trip W13, W14 or W15.
    """
    report = check_office_dir(office)
    tripped = [f for f in report.findings if f.code in _NEW]
    assert not tripped, "\n".join(
        f"{f.code} on {f.subject}: {f.message}" for f in tripped
    )
