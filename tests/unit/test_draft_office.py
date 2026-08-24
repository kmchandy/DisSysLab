"""An office that is still being described.

`Give me an office with Dan and Jay` comes before anyone has said what
Dan does. Until this existed there was no way to write that down: every
agent line needed a role, so a half-specified office was not a legal
file and lived in the assistant's head until it was finished — which is
exactly when the person building it most needs to see it.

These tests cover the four properties that make the half-built state
usable rather than merely tolerated:

* the line parses, and parses as *undecided* rather than as something
  else that happens to fit the grammar;
* an office holding one is a draft, with no flag to pass;
* `dsl check` reports its findings as remaining work and exits 0;
* running one is refused in a sentence about the missing decision.
"""
from __future__ import annotations

from pathlib import Path

from dissyslab.office.check_wiring import check_office_dir, format_report
from dissyslab.office.office_spec import (
    UNASSIGNED,
    draft_refusal,
    is_draft,
    unassigned_agents,
)
from dissyslab.office.parser import parse_office_dir

REPO_ROOT = Path(__file__).resolve().parents[2]


def _office(tmp_path: Path, body: str) -> Path:
    (tmp_path / "office.md").write_text(body, encoding="utf-8")
    return tmp_path


NAMES_ONLY = """# Office: draft

Agents:
Dan is unassigned.
Jay is unassigned.
"""

HALF = """# Office: draft

Sources: nasa_news(max_articles=10)
Sinks: console_printer

Agents:
Dan is a relevance_filter.
Jay is unassigned.

Connections:
nasa_news's destination is Dan.
"""


# ── it parses, and parses as undecided ────────────────────────────────


def test_the_first_sentence_of_a_conversation_is_a_legal_file(tmp_path):
    spec = parse_office_dir(_office(tmp_path, NAMES_ONLY))
    assert [a.agent_name for a in spec.agents] == ["Dan", "Jay"]
    assert all(a.role_name == UNASSIGNED for a in spec.agents)


def test_it_is_not_read_as_a_sub_office_path(tmp_path):
    """The regression this whole feature was found by.

    Before the branch existed the line still parsed: the role pattern
    rejected it, because the article in `is a <role>` is mandatory, and
    a legacy `name is <path>` fallback then read `unassigned` as a
    directory and made Jay a sub-office living in ./unassigned. Nothing
    said so, and it surfaced much later as a missing role file — a
    clear sentence about the wrong thing.
    """
    spec = parse_office_dir(_office(tmp_path, NAMES_ONLY))
    assert all(a.path is None for a in spec.agents)


def test_a_real_sub_office_still_parses_as_one(tmp_path):
    spec = parse_office_dir(
        _office(tmp_path, "# Office: t\n\nAgents:\nX is an office at ../news.\n")
    )
    assert spec.agents[0].path == "../news"


def test_the_new_branch_did_not_loosen_the_grammar(tmp_path):
    """`Jay is deduplicator.` must not become a role.

    The article is what is supposed to make the language rigid enough
    for `dsl check` to catch what a language model got wrong, and a new
    branch is only acceptable if it buys the one sentence it was
    written for and nothing else. The `unassigned` pattern is anchored
    on that literal word, so it cannot.

    This asserts less than it should, and the reason is in STATUS: the
    line is not rejected either. A legacy `name is <path>` fallback
    accepts any unmatched agent line as a sub-office path and sets both
    role_name and path to it, so a forgotten article gives three
    different answers depending on which library the name lives in --
    `Jay is summarizer.` runs correctly, `Jay is deduplicator.` fails at
    build with a sub-office path error, and `Jay is frobnicator.` is
    reported as a missing role file. All three were run. That predates
    this work and is a separate change; what matters here is that the
    branch added for drafts did not widen anything.
    """
    spec = parse_office_dir(
        _office(tmp_path, "# Office: t\n\nAgents:\nJay is deduplicator.\n")
    )
    assert spec.agents[0].path == "deduplicator"  # legacy fallback, not a role
    assert not is_draft(spec)


# ── draft-ness is a property, not a flag ──────────────────────────────


def test_an_office_with_an_undecided_agent_is_a_draft(tmp_path):
    assert is_draft(parse_office_dir(_office(tmp_path, NAMES_ONLY)))
    assert unassigned_agents(parse_office_dir(_office(tmp_path, HALF))) == ["Jay"]


def test_a_finished_office_is_not_a_draft(tmp_path):
    body = """# Office: t

Sources: nasa_news(max_articles=10)
Sinks: console_printer

Agents:
Jay is a summarizer.

Connections:
nasa_news's destination is Jay.
Jay's out is console_printer.
"""
    spec = parse_office_dir(_office(tmp_path, body))
    assert not is_draft(spec)
    assert unassigned_agents(spec) == []


# ── check reports work, not faults ────────────────────────────────────


def test_check_on_a_draft_succeeds(tmp_path):
    """Exit 0. An unfinished office is not a broken one, and reporting
    it as broken teaches a beginner that building is a sequence of
    errors."""
    report = check_office_dir(_office(tmp_path, NAMES_ONLY))
    assert report.draft
    assert report.ok
    assert not report.errors


def test_the_undecided_agent_is_named_as_a_missing_decision(tmp_path):
    report = check_office_dir(_office(tmp_path, NAMES_ONLY))
    g1 = [f for f in report.findings if f.code == "G1"]
    assert {f.subject for f in g1} == {"Dan", "Jay"}
    assert "no job yet" in g1[0].message


def test_no_role_file_is_not_reported_for_an_undecided_agent(tmp_path):
    """W6 would say "there is no roles/unassigned.md", which is true and
    useless: the office is not missing a file."""
    report = check_office_dir(_office(tmp_path, NAMES_ONLY))
    assert not [f for f in report.findings if f.code == "W6"]


def test_an_office_with_no_sink_is_reported(tmp_path):
    """The one fault a person cannot diagnose from the outside.

    Every other mistake announces itself. An office with no sink is
    structurally perfect, runs cleanly, exits zero and produces
    silence, and the reasonable conclusion from that is that the
    framework is broken.
    """
    report = check_office_dir(_office(tmp_path, NAMES_ONLY))
    assert [f for f in report.findings if f.code == "G2"]


def test_no_sink_is_an_error_in_a_finished_office(tmp_path):
    body = """# Office: t

Sources: nasa_news(max_articles=10)

Agents:
Jay is a summarizer.

Connections:
nasa_news's destination is Jay.
"""
    report = check_office_dir(_office(tmp_path, body))
    assert not report.draft
    assert [f for f in report.errors if f.code == "G2"]


def test_an_open_office_is_exempt_from_the_sink_rule(tmp_path):
    """Its Outputs are how work leaves it; the office that embeds it
    owns the sink."""
    body = """# Office: t

Inputs: in_
Outputs: out

Agents:
Jay is a summarizer.

Connections:
external's out is Jay.
Jay's out is external's out.
"""
    report = check_office_dir(_office(tmp_path, body))
    assert not [f for f in report.findings if f.code == "G2"]


def test_findings_are_worded_as_remaining_work(tmp_path):
    report = check_office_dir(_office(tmp_path, HALF))
    text = format_report(report)
    assert "still to do" in text
    assert "nothing reaches Jay yet" in text
    assert "unreachable" not in text


def test_a_misspelled_component_stays_an_error_in_a_draft(tmp_path):
    """Incompleteness is expected in a draft. A name that is in no
    registry is wrong now and will still be wrong when the office is
    finished, so calling it "remaining work" would bury it."""
    body = """# Office: draft

Sources: nasa_newz(max_articles=10)
Sinks: console_printer

Agents:
Jay is unassigned.
"""
    report = check_office_dir(_office(tmp_path, body))
    assert report.draft
    assert [f for f in report.errors if f.code == "W5"]
    assert not report.ok


# ── running one is refused, in a sentence ─────────────────────────────


def test_refusal_names_every_undecided_agent():
    msg = draft_refusal(["Dan", "Jay"])
    assert "'Dan' and 'Jay' have no job yet" in msg
    assert draft_refusal(["Dan"]).count("has no job yet") == 1


def test_run_and_build_refuse_a_draft(tmp_path):
    from dissyslab.cli import main

    office = _office(tmp_path, NAMES_ONLY)
    assert main(["run", str(office)]) == 1
    assert main(["build", str(office)]) == 1
    assert not (office / "build").exists()


# ── the reserved name has to stay reserved ────────────────────────────


def test_no_library_role_is_called_unassigned():
    """`unassigned` is a sentinel in `role_name`, which is a plain
    string. A role file of that name in the built-in library, or in an
    office's own roles/, would shadow the sentinel and make an
    undecided agent look decided. Nothing else prevents it, so this
    does."""
    library = REPO_ROOT / "dissyslab" / "roles"
    clashes = [p.name for p in library.iterdir() if p.stem == UNASSIGNED]
    assert not clashes, (
        f"{clashes} shadows the reserved role name {UNASSIGNED!r}. "
        "An agent with no job yet would be read as having one."
    )

    offices = list((REPO_ROOT / "dissyslab" / "gallery").glob("*/*/roles/*"))
    shadowed = [str(p) for p in offices if p.stem == UNASSIGNED]
    assert not shadowed, f"{shadowed} shadows {UNASSIGNED!r}."
