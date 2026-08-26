"""Text from the open web reaching something that acts.

The office below parses today, runs today, and `dsl check` reported it
as fine:

    Sources: web_scraper(url="...")
    Agents:  Alice is a summarizer.
    Sinks:   gmail_sink

A scraped page is written by a stranger. `summarizer` is a paragraph of
English run by a language model. A model that can be instructed can be
instructed by its input, so no wording of that paragraph closes the
path -- what can be closed is the other end. An office affects the
world only through its sinks, and an office whose sinks all print or
write a local file cannot attack anything however persuaded the middle
is.

So W11 asks the only question that is decidable here: can an untrusted
source reach an acting sink. It is reachability on the graph W3 and W4
already build.
"""
from __future__ import annotations

from pathlib import Path

from dissyslab.office import trust
from dissyslab.office.check_wiring import check_office_dir
from dissyslab.office.utils import SINK_REGISTRY, SOURCE_REGISTRY

REPO_ROOT = Path(__file__).resolve().parents[2]
GALLERY = REPO_ROOT / "dissyslab" / "gallery"


def _write(tmp_path: Path, body: str) -> Path:
    d = tmp_path / "office"
    d.mkdir(parents=True, exist_ok=True)
    (d / "office.md").write_text(body, encoding="utf-8")
    return d


def _codes(report) -> list[str]:
    return [f.code for f in report.findings]


# ── every component is classified ─────────────────────────────────────


def test_every_registered_component_is_classified():
    """The check that keeps the tables honest as components are added.

    A component nobody classified would be silently treated as trusted
    or inert, which is the safe-looking answer and the wrong one. Same
    shape as `emits:` on a role: the test is what turns "somebody
    should decide" into "somebody must".
    """
    missing = trust.unclassified(set(SOURCE_REGISTRY), set(SINK_REGISTRY))
    assert not missing["sources"] and not missing["sinks"], (
        f"unclassified: {missing}.\n"
        "Add each to dissyslab/office/trust.py. A source is untrusted "
        "when it carries free text someone else composed; a sink is "
        "acting when it affects something outside this machine."
    )


def test_the_two_classes_do_not_overlap():
    assert not (trust.UNTRUSTED_SOURCES & trust.TRUSTED_SOURCES)
    assert not (trust.ACTING_SINKS & trust.INERT_SINKS)


def test_every_acting_sink_can_say_what_it_does():
    """The message names the consequence -- "sends email" -- because
    "is an acting sink" is a category and not a thing a person can act
    on."""
    for name in trust.ACTING_SINKS:
        assert trust.what_it_does(name) != "acts outside this machine", (
            f"{name} has no phrase in _WHAT_IT_DOES"
        )


def test_an_unknown_name_is_not_treated_as_dangerous():
    """A check that fired on every component it had not heard of would
    fire on every office anyone extended, and a check people learn to
    skip protects nothing. The test above is what stops "unknown" from
    becoming the common case."""
    assert not trust.is_untrusted_source("something_nobody_registered")
    assert not trust.is_acting_sink("something_nobody_registered")


# ── the check itself ──────────────────────────────────────────────────


def test_the_live_hole_is_reported(tmp_path):
    """The whole bug in one office."""
    d = _write(tmp_path, """# Office: leaky

Sources: web_scraper(url="https://example.com")
Sinks: gmail_sink

Agents:
Alice is a summarizer.

Connections:
web_scraper's destination is Alice.
Alice's out is gmail_sink.
""")
    report = check_office_dir(d)
    w11 = [f for f in report.findings if f.code == "W11"]
    assert w11, "an office that mails whatever a scraped page said reported clean"
    assert "web_scraper" in w11[0].message
    assert "sends email" in w11[0].message


def test_an_inert_sink_is_not_reported(tmp_path):
    """The same office, ending at the screen. Nothing leaves the
    machine, so there is nothing to say -- and saying it anyway is how
    a check becomes noise."""
    d = _write(tmp_path, """# Office: quiet

Sources: web_scraper(url="https://example.com")
Sinks: console_printer

Agents:
Alice is a summarizer.

Connections:
web_scraper's destination is Alice.
Alice's out is console_printer.
""")
    assert "W11" not in _codes(check_office_dir(d))


def test_a_trusted_source_is_not_reported(tmp_path):
    """Mailing a summary of the user's own file is not this problem."""
    d = _write(tmp_path, """# Office: mine

Sources: file_source(path="notes.txt")
Sinks: gmail_sink

Agents:
Alice is a summarizer.

Connections:
file_source's destination is Alice.
Alice's out is gmail_sink.
""")
    assert "W11" not in _codes(check_office_dir(d))


def test_an_unconnected_pair_is_not_reported(tmp_path):
    """Both a web source and a mail sink, with no path between them.
    The finding is about reachability, not about the guest list."""
    d = _write(tmp_path, """# Office: parallel

Sources: web_scraper(url="https://example.com"), file_source(path="notes.txt")
Sinks: console_printer, gmail_sink

Agents:
Alice is a summarizer.
Bob is a summarizer.

Connections:
web_scraper's destination is Alice.
Alice's out is console_printer.
file_source's destination is Bob.
Bob's out is gmail_sink.
""")
    assert "W11" not in _codes(check_office_dir(d))


def test_it_is_a_note_and_does_not_fail_the_check(tmp_path):
    """Deliberate. There is no gate concept yet, so this cannot tell a
    guarded path from an unguarded one, and an error on an office
    somebody built on purpose teaches them to skip the section it
    prints in -- taking the real findings with it."""
    d = _write(tmp_path, """# Office: leaky

Sources: web_scraper(url="https://example.com")
Sinks: gmail_sink

Agents:
Alice is a summarizer.

Connections:
web_scraper's destination is Alice.
Alice's out is gmail_sink.
""")
    report = check_office_dir(d)
    assert [f for f in report.findings if f.code == "W11"]
    assert all(f.code != "W11" for f in report.errors)
    assert report.ok


def test_sinks_behind_the_same_sources_are_one_finding(tmp_path):
    """`job_hunter` has four Gmail sinks behind one set of job boards.
    Four notes about one shape reads as four things to think about --
    the same reason W4 reports a frontier."""
    d = _write(tmp_path, """# Office: many_sinks

Sources: hacker_news
Sinks: gmail_sink_match, gmail_sink_research

Agents:
Alice is a summarizer.

Connections:
hacker_news's destination is Alice.
Alice's out is gmail_sink_match, gmail_sink_research.
""")
    w11 = [f for f in check_office_dir(d).findings if f.code == "W11"]
    assert len(w11) == 1
    assert "gmail_sink_match" in w11[0].message
    assert "gmail_sink_research" in w11[0].message


def test_a_long_path_is_still_found(tmp_path):
    """Reachability, not adjacency. The office that gets built by
    accident has several agents between the feed and the sink, added on
    different days."""
    d = _write(tmp_path, """# Office: chain

Sources: rss(url="https://example.com/feed", name="rss")
Sinks: slack_sink

Agents:
Alice is a summarizer.
Bob is a topic_tagger.
Cara is a writer.

Connections:
rss's destination is Alice.
Alice's out is Bob.
Bob's out is Cara.
Cara's out is slack_sink.
""")
    assert "W11" in _codes(check_office_dir(d))


# ── the shipped offices ───────────────────────────────────────────────


def test_the_shipped_offices_that_fire_are_the_ones_we_expect():
    """Pinned, so that adding a sink to a gallery office is a decision
    rather than a surprise -- and so that a change to the tables shows
    up here as a diff rather than as silence.

    All five are real: each genuinely carries other people's words to
    something that leaves the machine. They are shipped as they are
    because that is what those offices are *for*; the note is the
    office saying so out loud.
    """
    firing = set()
    for office_md in sorted(GALLERY.rglob("office.md")):
        try:
            report = check_office_dir(office_md.parent)
        except Exception:  # noqa: BLE001 - a broken office is another test's problem
            continue
        if any(f.code == "W11" for f in report.findings):
            firing.add(office_md.parent.name)

    assert firing == {
        "inbox_triage",
        "job_hunter",
        "lead_qualifier",
        "situation_room_requests",
        "ticket_router",
    }
