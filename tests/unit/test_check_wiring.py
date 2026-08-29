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


# ── W2: an outbox the role declares and nothing is wired to ───────────


def _office(tmp_path, office_md: str, roles: dict[str, str] | None = None):
    d = tmp_path / "office"
    (d / "roles").mkdir(parents=True, exist_ok=True)
    (d / "office.md").write_text(office_md, encoding="utf-8")
    for name, body in (roles or {}).items():
        (d / "roles" / name).write_text(body, encoding="utf-8")
    return d


_FILTER = """---
emits: keeps some items
outboxes: keep, discard
---
# Role: my_filter

If the item is relevant, send to keep. Otherwise send to discard.
"""

_TWO_PORT_OFFICE = """# Office: x

Sources: starter
Sinks: console_printer

Agents:
Screen is a my_filter.

Connections:
starter's destination is Screen.
Screen's keep is console_printer.
"""


def test_w2_catches_an_outbox_nothing_is_wired_to(tmp_path):
    """The office is structurally perfect and crashes on the first item
    it wants to discard: `send` raises on an outbox with no queue. For a
    filter, discarding something is the normal case, so this is not an
    edge -- it is the second message."""
    from dissyslab.office.check_wiring import check_office_dir

    d = _office(tmp_path, _TWO_PORT_OFFICE, {"my_filter.md": _FILTER})
    report = check_office_dir(d)
    w2 = [f for f in report.findings if f.code == "W2"]
    assert len(w2) == 1
    assert "discard" in w2[0].message
    assert not report.ok, "an outbox that will raise is a fault, not a note"


def test_w2_is_silent_when_every_declared_outbox_is_wired(tmp_path):
    from dissyslab.office.check_wiring import check_office_dir

    d = _office(
        tmp_path,
        _TWO_PORT_OFFICE + "Screen's discard is discard.\n",
        {"my_filter.md": _FILTER},
    )
    assert not [f for f in check_office_dir(d).findings if f.code == "W2"]


def test_the_backtick_trap_no_longer_exists(tmp_path):
    """The trap the whole change was made to close.

    ``send to `keep` `` -- backticks, as any careful writer puts round a
    port name -- used to create no port at all. The office checked
    clean and produced nothing, and no check could see it, because the
    ports came from the prose and there was no declaration to disagree
    with.

    Now the prose is prose. The declaration says ``keep, discard``, so
    W2 names ``discard`` here exactly as it does without backticks, and
    the writer's formatting has stopped being load-bearing.
    """
    from dissyslab.office.check_wiring import check_office_dir

    backticked = _FILTER.replace("send to keep", "send to `keep`").replace(
        "send to discard", "send to `discard`"
    )
    d = _office(tmp_path, _TWO_PORT_OFFICE, {"my_filter.md": backticked})
    w2 = [f for f in check_office_dir(d).findings if f.code == "W2"]
    assert len(w2) == 1 and "discard" in w2[0].message


def test_a_python_role_shadows_the_prose_one(tmp_path):
    """`mac_speed_suite` ships `roles/evaluator.py`, which shadows the
    library's prose `evaluator.md`. Read the wrong file and the check
    invents a fault in a working office -- the first version of this
    check did exactly that.

    A `.py` role is no longer exempt: its ports are read out of the
    ``AgentRoleEntry`` it builds, by AST and without importing it. So
    what this pins now is *which* file gets read. The `.py` declares
    one outbox, `keep`, and it is wired; the `.md` beside it declares
    two. Reading the `.md` would report `discard` unwired on an office
    that is right.
    """
    from dissyslab.office.check_wiring import check_office_dir

    d = _office(
        tmp_path,
        _TWO_PORT_OFFICE,
        {
            "my_filter.md": _FILTER,
            "my_filter.py": (
                "from dissyslab.office.library import AgentRoleEntry\n"
                "role = AgentRoleEntry(name='my_filter', in_ports=('in_',),\n"
                "                      out_ports=('keep',),\n"
                "                      factory=lambda: None)\n"
            ),
        },
    )
    assert not [f for f in check_office_dir(d).findings if f.code == "W2"]


def test_in_a_draft_it_is_remaining_work(tmp_path):
    from dissyslab.office.check_wiring import check_office_dir, format_report

    d = _office(
        tmp_path,
        _TWO_PORT_OFFICE.replace(
            "Screen is a my_filter.", "Screen is a my_filter.\nLater is unassigned."
        ),
        {"my_filter.md": _FILTER},
    )
    report = check_office_dir(d)
    assert report.ok, "an unfinished sketch is not a broken office"
    assert "still to do" in format_report(report)


def test_no_shipped_office_trips_it():
    """Pinned. A check that fires on things people meant is one they
    learn to skim, and it takes the true findings with it."""
    from pathlib import Path

    from dissyslab.office.check_wiring import check_office_dir

    gallery = Path(__file__).resolve().parents[2] / "dissyslab" / "gallery"
    firing = set()
    for office_md in sorted(gallery.rglob("office.md")):
        try:
            report = check_office_dir(office_md.parent)
        except Exception:  # noqa: BLE001 - other checks cover parse failures
            continue
        if [f for f in report.findings if f.code == "W2"]:
            firing.add(office_md.parent.name)
    assert firing == set()


# ── W13 and W1: the inbox half, now that roles declare their inboxes ──
#
# W13 is new and W1 grew. Before roles declared inboxes, the only agents
# with a known inbox set were the three coordinator kinds that spell
# theirs on the agent line, so W1 checked those and W13 could not exist
# at all. A misspelled destination -- `Screen's inbx is ...` -- passed
# every check, built a connection to a port that was never created, and
# failed at run time with
#
#     Agent 'Screen' inport 'in_' is not connected to any queue
#
# naming `in_`, a port the writer never typed, about a line they did.


_ONE_INBOX_OFFICE = """\
# Office: x

Sources: starter
Sinks: console_printer

Agents:
Screen is a my_filter.

Connections:
starter's destination is Screen{port}.
Screen's keep is console_printer.
Screen's discard is console_printer.
"""


def test_w13_catches_a_message_sent_to_an_inbox_that_does_not_exist(tmp_path):
    d = _office(
        tmp_path,
        _ONE_INBOX_OFFICE.format(port="'s inbx"),
        {"my_filter.md": _FILTER},
    )
    report = check_office_dir(d)
    w13 = [f for f in report.findings if f.code == "W13"]
    assert len(w13) == 1
    assert "inbx" in w13[0].message and "starter" in w13[0].message
    assert not report.ok, "a message that reaches nothing is a fault"
    # The fix is named, and it is the one the writer can act on.
    assert "in_" in w13[0].hint


def test_w13_is_silent_when_the_inbox_is_spelt_right(tmp_path):
    d = _office(
        tmp_path, _ONE_INBOX_OFFICE.format(port=""), {"my_filter.md": _FILTER}
    )
    report = check_office_dir(d)
    assert not [f for f in report.findings if f.code == "W13"]
    assert report.ok


def test_one_typo_gives_one_finding(tmp_path):
    """A misspelled destination leaves the real inbox unwired by
    construction, so W1 would fire too -- the same mistake said twice.
    Fixing the spelling fixes both, so only W13 is reported."""
    d = _office(
        tmp_path,
        _ONE_INBOX_OFFICE.format(port="'s inbx"),
        {"my_filter.md": _FILTER},
    )
    codes = [f.code for f in check_office_dir(d).findings]
    assert codes.count("W13") == 1
    assert "W1" not in codes


def test_w1_now_covers_an_agent_whose_role_declares_its_inboxes(tmp_path):
    """W1 used to reach only the coordinators. A two-inbox prose role
    with one of them unwired is the ordinary case, and it was silent."""
    two_in = _FILTER.replace(
        "emits: keeps some items",
        "emits: keeps some items\ninboxes: articles, rules",
    )
    body = """\
# Office: x

Sources: starter
Sinks: console_printer

Agents:
Screen is a my_filter.

Connections:
starter's destination is Screen's articles.
Screen's keep is console_printer.
Screen's discard is console_printer.
"""
    report = check_office_dir(_office(tmp_path, body, {"my_filter.md": two_in}))
    w1 = [f for f in report.findings if f.code == "W1"]
    assert len(w1) == 1 and "rules" in w1[0].message


def test_an_unreachable_agent_is_not_also_reported_as_a_blocked_one(tmp_path):
    """Nothing reaches the agent at all. W3 says that once and says
    why; a W1 per inbox on top of it buries the finding that leads
    somewhere."""
    body = """\
# Office: x

Sources: starter
Sinks: console_printer

Agents:
A is a summarizer.
Screen is a my_filter.

Connections:
starter's destination is A.
A's out is console_printer.
Screen's keep is console_printer.
Screen's discard is console_printer.
"""
    codes = [
        f.code
        for f in check_office_dir(_office(tmp_path, body, {"my_filter.md": _FILTER})).findings
    ]
    assert "W3" in codes
    assert "W1" not in codes


def test_a_coordinators_command_inbox_is_not_a_typo(tmp_path):
    """`select(inboxes=[...], command='command')` has three inboxes, not
    two: the command port is named in an argument of its own. Missing it
    made `CLERK's command is SELECT's command.` -- a line two shipped
    offices depend on -- look like a message sent nowhere."""
    from dissyslab.office.check_wiring import declared_inports

    class _Spec:
        args = (("inports", ["ticket", "manager_reply"]), ("command", "command"))

    assert declared_inports(_Spec()) == ["ticket", "manager_reply", "command"]


def test_no_shipped_office_trips_the_inbox_checks():
    """Pinned, the same way W2 is. Both new behaviours are silent on
    every office we ship."""
    from pathlib import Path

    gallery = Path(__file__).resolve().parents[2] / "dissyslab" / "gallery"
    firing = {}
    for office_md in sorted(gallery.rglob("office.md")):
        try:
            report = check_office_dir(office_md.parent)
        except Exception:  # noqa: BLE001 - other checks cover parse failures
            continue
        hits = [f.code for f in report.findings if f.code in ("W1", "W13")]
        if hits:
            firing[office_md.parent.name] = hits
    assert firing == {}


def test_w13_prints_the_corrected_line_when_there_is_one_inbox(tmp_path):
    """The hint is the sentence to type, not a sentence with a gap.

    An agent with one inbox is the ordinary case, and the default inbox
    `in_` is not named in a connection at all -- which is exactly the
    part a beginner will not guess. So the hint writes the whole line
    out, sending port included.
    """
    d = _office(
        tmp_path,
        _ONE_INBOX_OFFICE.format(port="'s inbx"),
        {"my_filter.md": _FILTER},
    )
    hint = [f for f in check_office_dir(d).findings if f.code == "W13"][0].hint
    assert "Write: starter's destination is Screen." in hint
