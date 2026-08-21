"""Tests for ``dsl check`` — the structural checker.

``check_wiring`` shipped in 1.7.0 with no unit tests; its acceptance was
four deliberate breaks run by hand against ``situation_room``. That is a
good acceptance test and a bad regression test — it does not run again.
This file pins the behaviour the hand-checks established.

The offices here are written inline rather than taken from the gallery
so that a change to a gallery app cannot silently change what these
assert.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from dissyslab.office.check_wiring import check_office_dir, format_report


OK_OFFICE = """\
# Office: t

Sources: starter
Sinks: console_printer

Agents:
A is a summarizer.
B is a summarizer.

Connections:
starter sends its out to A.
A sends its out to B.
B sends its out to console_printer.
"""


def write_office(tmp_path: Path, text: str) -> Path:
    d = tmp_path / "office"
    d.mkdir(parents=True, exist_ok=True)
    (d / "office.md").write_text(text, encoding="utf-8")
    return d


def codes(report) -> list[str]:
    return [f.code for f in report.findings]


def test_a_correct_office_is_clean():
    """The baseline. If this fails, every other test here is noise."""
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        d = write_office(Path(td), OK_OFFICE)
        report = check_office_dir(d)
        assert codes(report) == [], format_report(report)


def test_unfed_sink_is_reported_once(tmp_path):
    """W8 — the sink nobody writes to. This is the fault that shipped in
    four gallery offices and produced four zero-byte .jsonl files."""
    text = OK_OFFICE.replace(
        "Sinks: console_printer",
        "Sinks: console_printer, discard",
    )
    report = check_office_dir(write_office(tmp_path, text))
    assert codes(report).count("W8") == 1
    assert "discard" in format_report(report)


def test_misspelled_agent_in_connections(tmp_path):
    """W9 — a name in Connections that is declared nowhere."""
    text = OK_OFFICE.replace("A sends its out to B.", "A sends its out to Bea.")
    report = check_office_dir(write_office(tmp_path, text))
    assert "W9" in codes(report)
    assert "Bea" in format_report(report)


# ── W4: the cascade frontier ────────────────────────────────────────────
#
# Cutting one wire near the sinks makes every agent upstream of the cut a
# dead end. Reporting each of them is correct and useless: seven findings
# for one missing wire reads to a first-year as seven separate problems,
# and none of the seven says where to look. The checker reports the
# frontier -- the agent where the path to a sink actually stops -- and
# counts the rest.


DEAD_CHAIN = """\
# Office: t

Sources: starter
Sinks: console_printer

Agents:
A is a summarizer.
B is a summarizer.
C is a summarizer.

Connections:
starter sends its out to A.
A sends its out to B.
B sends its out to C.
"""


def test_w4_reports_only_the_frontier(tmp_path):
    """A -> B -> C, with C wired to nothing. All three are dead ends;
    only C is where the break is."""
    report = check_office_dir(write_office(tmp_path, DEAD_CHAIN))
    w4 = [f for f in report.findings if f.code == "W4"]
    assert len(w4) == 1, (
        f"expected one W4 at the frontier, got "
        f"{[f.subject for f in w4]}\n{format_report(report)}"
    )
    assert w4[0].subject == "C"


def test_w4_counts_the_agents_it_did_not_list(tmp_path):
    """Suppressing the cascade must not hide it. The upstream agents are
    still affected and the report says how many."""
    report = check_office_dir(write_office(tmp_path, DEAD_CHAIN))
    text = format_report(report)
    assert "2 agent(s) upstream" in text
    # Named, so the reader can confirm the diagnosis rather than trust it.
    assert "A" in text and "B" in text


def test_w4_still_fires_for_two_independent_breaks(tmp_path):
    """Two separate dead branches are two separate problems, and both
    must be reported. Collapsing a cascade must not collapse across
    unrelated faults."""
    text = """\
# Office: t

Sources: starter
Sinks: console_printer

Agents:
Hub is a summarizer.
Left is a summarizer.
Right is a summarizer.

Connections:
starter sends its out to Hub.
Hub sends its out to Left, Right.
"""
    report = check_office_dir(write_office(tmp_path, text))
    w4 = sorted(f.subject for f in report.findings if f.code == "W4")
    assert w4 == ["Left", "Right"], format_report(report)


def test_exit_code_is_nonzero_only_for_errors(tmp_path):
    """A clean office exits 0; a fault exits non-zero. The build loop in
    the skill depends on this, and so does CI."""
    from dissyslab.office.check_wiring import main

    good = write_office(tmp_path / "g", OK_OFFICE)
    bad = write_office(tmp_path / "b", DEAD_CHAIN)
    assert main([str(good)]) == 0
    assert main([str(bad)]) != 0


# ── W5: a source or sink that does not exist ────────────────────────────
#
# Found by the E5 acceptance trial. Before this, `Sources: bbc_wolrd`
# passed `dsl check` clean, passed `dsl build` clean, and died at run time
# with `NameError: name 'bbc_wolrd' is not defined` pointing into
# generated code the student never wrote. W6 covered role names only, and
# the skill's promise that the check catches unknown names read as though
# it covered these too. Check clean, build clean, traceback is the exact
# sequence the checker exists to prevent.


TYPO_SOURCE = """\
# Office: t

Sources: bbc_wolrd
Sinks: console_printer

Agents:
A is a summarizer.

Connections:
bbc_wolrd sends its out to A.
A sends its out to console_printer.
"""


def test_w5_catches_a_misspelled_source(tmp_path):
    report = check_office_dir(write_office(tmp_path, TYPO_SOURCE))
    assert "W5" in codes(report), format_report(report)


def test_w5_suggests_the_right_spelling(tmp_path):
    """A typo's whole value as a diagnostic is that the answer is one
    character away. Saying only 'no such source' wastes that."""
    report = check_office_dir(write_office(tmp_path, TYPO_SOURCE))
    assert "bbc_world" in format_report(report)


def test_w5_catches_an_invented_sink(tmp_path):
    text = OK_OFFICE.replace(
        "Sinks: console_printer", "Sinks: totally_fake_sink"
    ).replace("console_printer.", "totally_fake_sink.")
    report = check_office_dir(write_office(tmp_path, text))
    w5 = [f for f in report.findings if f.code == "W5"]
    assert [f.subject for f in w5] == ["totally_fake_sink"], format_report(report)


def test_w5_does_not_fire_on_real_components(tmp_path):
    """The cost of a false W5 is a student deleting a line that was
    right, so this is the assertion that matters most."""
    report = check_office_dir(write_office(tmp_path, OK_OFFICE))
    assert not [f for f in report.findings if f.code == "W5"], format_report(report)


@pytest.mark.parametrize("office_name", ["periodic_brief", "situation_room"])
def test_shipped_offices_pass(office_name):
    """The gallery is the free regression suite: every shipped office
    must check clean. Two representatives run here on every commit; the
    full sweep of all 30 is in the release procedure."""
    import dissyslab.gallery as gallery

    d = Path(gallery.__file__).parent / "apps" / office_name
    if not (d / "office.md").exists():
        pytest.skip(f"{office_name} not installed")
    report = check_office_dir(d)
    errors = [f for f in report.findings if f.severity == "error"]
    assert not errors, format_report(report)


# ── The inboxes / inports alias ──────────────────────────────────────────


def test_both_mailbox_spellings_normalise_to_one():
    """office.md now says ``inboxes=``; the framework still calls the
    same thing ``inports`` internally. RoleRef.__post_init__ is the one
    place every office.md role reference passes through, so normalising
    there means every consumer downstream sees a single spelling — and
    an office written before the rename still compiles.
    """
    from dissyslab.office.office_spec import RoleRef

    old = RoleRef(
        agent_name="Sync", role_name="synchronizer",
        args=(("inports", ["a", "b"]),),
    )
    new = RoleRef(
        agent_name="Sync", role_name="synchronizer",
        args=(("inboxes", ["a", "b"]),),
    )

    assert old.args == new.args == (("inports", ["a", "b"]),)


def test_the_alias_leaves_other_arguments_alone():
    from dissyslab.office.office_spec import RoleRef

    ref = RoleRef(
        agent_name="Sasha", role_name="deduplicator",
        args=(("by", "url"), ("outboxes", ["keep", "drop"])),
    )

    assert ref.args == (("by", "url"), ("outports", ["keep", "drop"]))
