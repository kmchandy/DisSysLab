"""The parser for the line form of office files (spec section 3.1).

Two kinds of test:

- unit tests of each rule in section 3.1 (what is forgiven, what is not);
- every complete office file shown in the spec and in the nine paper
  ports (docs/internals/design/officespeak_ports/) must parse. Those
  files are what students and the microcourse will copy, so a document
  showing an office the parser rejects is a fault in one or the other.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from dissyslab.office.model import Connection, PortRef
from dissyslab.office.syntax import OfficeSyntaxError, parse_office_text

REPO = Path(__file__).resolve().parents[2]
DESIGN = REPO / "docs" / "internals" / "design"

ROOM = """\
# room_climate_monitor: alert when the room is both hot and humid

sources:
    temp_sensor: file_source(path="temp.jsonl")
    humidity_sensor: file_source(path="humidity.jsonl")

sinks:
    console_printer
    discard

agents:
    Join: synchronizer(on="slot")
    Checker: checker(max_temp=80, max_humidity=60)
    Rex: router(on="alert")

connections:
    temp_sensor -> Join.temp
    humidity_sensor -> Join.humidity
    Join -> Checker -> Rex
    Rex.yes -> console_printer
    Rex.no -> discard
"""


def arrows(office) -> list[str]:
    return [f"{c.sender.name}.{c.out_port} -> {c.receiver.name}.{c.in_port}"
            for c in office.connections]


# ── The example in section 3.1 ─────────────────────────────────────────────


def test_the_spec_example():
    office = parse_office_text(ROOM)
    assert [d.name for d in office.sources] == ["temp_sensor", "humidity_sensor"]
    assert office.sources[0].kind == "file_source"
    assert office.sources[0].args == {"path": "temp.jsonl"}
    assert [(d.name, d.kind) for d in office.sinks] == [
        ("console_printer", "console_printer"), ("discard", "discard")]
    assert office.agents[1].args == {"max_temp": 80, "max_humidity": 60}
    assert arrows(office) == [
        "temp_sensor.out -> Join.temp",
        "humidity_sensor.out -> Join.humidity",
        "Join.out -> Checker.in",
        "Checker.out -> Rex.in",
        "Rex.yes -> console_printer.in",
        "Rex.no -> discard.in",
    ]
    assert office.inboxes_of("Join") == ["temp", "humidity"]
    assert office.names["Rex"] == 14


# ── Connections ────────────────────────────────────────────────────────────


def _with(connections: str, names: str = "a b c d") -> str:
    decls = "\n".join(f"    {n}: role" for n in names.split())
    return f"agents:\n{decls}\nconnections:\n    {connections}\n"


def test_chain_fan_out_and_fan_in():
    assert arrows(parse_office_text(_with("a -> b -> c"))) == [
        "a.out -> b.in", "b.out -> c.in"]
    assert arrows(parse_office_text(_with("a -> b, c, d"))) == [
        "a.out -> b.in", "a.out -> c.in", "a.out -> d.in"]
    assert arrows(parse_office_text(_with("a, b -> c -> d"))) == [
        "a.out -> c.in", "b.out -> c.in", "c.out -> d.in"]


def test_a_list_only_at_either_end_of_a_chain():
    with pytest.raises(OfficeSyntaxError, match="either end"):
        parse_office_text(_with("a -> b, c -> d"))


def test_named_ports_and_the_unicode_arrow():
    office = parse_office_text(_with("a.yes → b.left"))
    assert office.connections == (
        Connection(PortRef("a", "yes"), PortRef("b", "left"), line=7),)


def test_an_undeclared_name_is_an_error_with_a_suggestion():
    with pytest.raises(OfficeSyntaxError, match="'Chekcer' is not declared. Did you mean 'Checker'"):
        parse_office_text(ROOM.replace("Join -> Checker", "Join -> Chekcer"))


def test_a_connection_outside_connections_is_an_error():
    with pytest.raises(OfficeSyntaxError, match="connections go under connections:"):
        parse_office_text("agents:\n    a: role\n    a -> a\n")


# ── Declarations and arguments ─────────────────────────────────────────────


@pytest.mark.parametrize("line, kind, args", [
    ("x: role", "role", {}),
    ("x: role()", "role", {}),
    ("x: role(a=1, b='two', c=\"three\")", "role", {"a": 1, "b": "two", "c": "three"}),
    ("x: role(flag=true, other=False)", "role", {"flag": True, "other": False}),
    ("x: role(xs=[1, 2, 3], d={'k': 'v'})", "role", {"xs": [1, 2, 3], "d": {"k": "v"}}),
    ("x: role(a=1,)", "role", {"a": 1}),
    ("x: role(a=1).", "role", {"a": 1}),
    ("x: role(path='notes#1.txt')  # a comment", "role", {"path": "notes#1.txt"}),
])
def test_declarations_are_forgiving(line, kind, args):
    (decl,) = parse_office_text(f"AGENTS:\n  {line}\n").agents
    assert (decl.name, decl.kind, decl.args) == ("x", kind, args)


def test_a_bare_kind_is_named_after_itself():
    (decl,) = parse_office_text("sources:\n    bbc_world(max_articles=3)\n").sources
    assert (decl.name, decl.kind, decl.args) == ("bbc_world", "bbc_world", {"max_articles": 3})


def test_a_declaration_may_continue_while_a_bracket_is_open():
    office = parse_office_text(
        "sinks:\n"
        "    intelligence_display(title=\"title\", text=\"abstract\",\n"
        "                         lines=[\"authors\",\n"
        "                                \"reason\"])\n"
        "    discard\n")
    assert office.sinks[0].args["lines"] == ["authors", "reason"]
    assert office.sinks[0].line == 2
    assert office.sinks[1].line == 5


@pytest.mark.parametrize("line, message", [
    ("x: role(1)", "arguments are named"),
    ("x: role(a=b)", "must be written out"),
    ("x: role(a=__import__('os'))", "must be written out"),
    ("x: role(**opts)", r"\*\* is not allowed"),
    ("x: 3", "expected kind or kind"),
    ("x: role(a=1", "cannot read"),
])
def test_declarations_that_are_not_forgiven(line, message):
    with pytest.raises(OfficeSyntaxError, match=message):
        parse_office_text(f"agents:\n    {line}\n")


def test_a_name_declared_twice_is_an_error():
    with pytest.raises(OfficeSyntaxError, match="already declared on line 2"):
        parse_office_text("agents:\n    a: role\n    a: other\n")


# ── Sections ───────────────────────────────────────────────────────────────


def test_inputs_and_outputs_of_a_nested_office():
    office = parse_office_text(
        "inputs:\n    articles\noutputs:\n    kept, dropped\n"
        "agents:\n    F: f\nconnections:\n    articles -> F -> kept\n")
    assert office.inputs == ("articles",)
    assert office.outputs == ("kept", "dropped")
    assert arrows(office) == ["articles.out -> F.in", "F.out -> kept.in"]


@pytest.mark.parametrize("text, message", [
    ("a: role\n", "not under any section"),
    ("agent:\n    a: role\n", "no section called 'agent'. Did you mean 'agents'"),
    ("Sources: bbc_world, npr_news\n", "a section heading stands alone"),
    ("agents:\n    Rex is a router(on=\"v\").\n", "old sentence form"),
    ("connections:\n    Eve's out is Rex.\n", "old sentence form"),
])
def test_section_errors(text, message):
    with pytest.raises(OfficeSyntaxError, match=message):
        parse_office_text(text)


def test_errors_name_the_line():
    with pytest.raises(OfficeSyntaxError) as info:
        parse_office_text(ROOM.replace("Rex: router", "Rex: router(1)"))
    assert info.value.line == 14


# ── Every complete office in the spec and the paper ports parses ───────────


def _office_blocks():
    """(file name, block) for every fenced block that is a complete office."""
    fence = re.compile(r"^```(\w*)\n(.*?)^```", re.M | re.S)
    docs = sorted((DESIGN / "officespeak_ports").glob("*.md"))
    docs.append(DESIGN / "officespeak_revised.md")
    for doc in docs:
        for lang, block in fence.findall(doc.read_text(encoding="utf-8")):
            complete = re.search(r"^(sources|inputs):", block, re.M)
            if not lang and complete and re.search(r"^connections:", block, re.M):
                yield pytest.param(block, id=f"{doc.stem}:{block.splitlines()[0][:30]}")


BLOCKS = list(_office_blocks())


def test_the_documents_show_enough_offices():
    # Nine ports plus the spec's own examples; a fence change that hides
    # them would make the test below pass vacuously.
    assert len(BLOCKS) >= 12


@pytest.mark.parametrize("block", BLOCKS)
def test_every_office_in_the_documents_parses(block):
    office = parse_office_text(block)
    assert office.connections
