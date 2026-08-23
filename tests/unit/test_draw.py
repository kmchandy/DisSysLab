"""Tests for ``dissyslab.office.draw``.

These check that the picture says what the office says -- every node,
every edge, every port name the user chose. They deliberately do not
check *how* it is drawn. The diagram is produced on request rather
than after every edit, so nobody is comparing two of them, and pinning
the styling in a test would only make the styling harder to improve.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from dissyslab.office.draw import draw_office_dir, draw_spec, fenced
from dissyslab.office.parser import parse_office_dir

REPO_ROOT = Path(__file__).resolve().parents[2]
GALLERY = REPO_ROOT / "dissyslab" / "gallery"


def _write(tmp_path: Path, body: str) -> Path:
    (tmp_path / "office.md").write_text(body, encoding="utf-8")
    return tmp_path


def _edges(diagram: str) -> set[tuple[str, str, str]]:
    """(sender, label, receiver) for every arrow, label '' if absent."""
    out = set()
    for line in diagram.splitlines():
        m = re.match(r"\s*(\w+)\s+-->(?:\|([^|]*)\|)?\s+(\w+)\s*$", line)
        if m:
            out.add((m.group(1), (m.group(2) or "").strip(), m.group(3)))
    return out


def _node_ids(diagram: str) -> set[str]:
    return set(re.findall(r"^\s{2}(\w+)\[", diagram, re.M))


SIMPLE = """# Office: t

Sources: hacker_news(max_articles=10)
Sinks: console_printer, discard

Agents:
Dan is a relevance_filter.
Jay is a summarizer.

Connections:
hacker_news's destination is Dan.
Dan's keep is Jay.
Dan's discard is discard.
Jay's out is console_printer.
"""


def test_every_declared_name_becomes_a_node(tmp_path):
    d = draw_office_dir(_write(tmp_path, SIMPLE))
    assert _node_ids(d) == {
        "hacker_news", "console_printer", "discard", "Dan", "Jay",
    }


def test_every_connection_becomes_an_edge(tmp_path):
    assert _edges(draw_office_dir(_write(tmp_path, SIMPLE))) == {
        ("hacker_news", "", "Dan"),
        ("Dan", "keep", "Jay"),
        ("Dan", "discard", "discard"),
        ("Jay", "", "console_printer"),
    }


def test_default_ports_are_not_labelled(tmp_path):
    """`out`, `destination` and `in_` are what the user did not choose.

    Naming them puts a word on every arrow that the reader cannot act
    on, and buries the one arrow whose name is the whole point.
    """
    labels = {lbl for _, lbl, _ in _edges(draw_office_dir(_write(tmp_path, SIMPLE)))}
    assert labels == {"", "keep", "discard"}


def test_a_named_inbox_is_labelled_without_a_second_arrow(tmp_path):
    body = """# Office: t

Sources: bbc_world
Sinks: console_printer

Agents:
Eve is an entity_extractor.
Sync is a synchronizer(inboxes=["entities"]).

Connections:
bbc_world's destination is Eve.
Eve's out is Sync's entities.
Sync's out is console_printer.
"""
    assert ("Eve", "entities", "Sync") in _edges(draw_office_dir(_write(tmp_path, body)))


def test_the_role_is_shown_with_the_agent(tmp_path):
    d = draw_office_dir(_write(tmp_path, SIMPLE))
    assert "Dan[Dan<br/>relevance_filter]" in d
    assert "Jay[Jay<br/>summarizer]" in d


def test_a_name_used_but_never_declared_still_gets_a_node(tmp_path):
    """An office that will not compile is when a picture helps most.

    Refusing to draw it would withhold the diagram at the only moment
    the reader has a real question.
    """
    body = """# Office: t

Sources: hacker_news
Sinks: console_printer

Agents:
Dan is a summarizer.

Connections:
hacker_news's destination is Dan.
Dan's out is Ghost.
Ghost's out is console_printer.
"""
    d = draw_office_dir(_write(tmp_path, body))
    assert "Ghost[Ghost<br/>not declared]" in d
    assert ("Dan", "", "Ghost") in _edges(d)


def test_output_is_deterministic(tmp_path):
    spec = parse_office_dir(_write(tmp_path, SIMPLE))
    assert draw_spec(spec) == draw_spec(spec)


def test_declaration_order_is_preserved(tmp_path):
    """So that a drawing of a changed office differs only where the
    office differs, and a diff of two diagrams is readable."""
    d = draw_office_dir(_write(tmp_path, SIMPLE))
    ids = [m for m in re.findall(r"^\s{2}(\w+)\[", d, re.M)]
    assert ids == ["hacker_news", "Dan", "Jay", "console_printer", "discard"]


def test_fenced_wraps_for_markdown():
    assert fenced("flowchart LR").splitlines()[0] == "```mermaid"


def _gallery_offices() -> list[Path]:
    return sorted(p.parent for p in GALLERY.glob("*/*/office.md"))


@pytest.mark.parametrize(
    "office_dir", _gallery_offices(), ids=lambda p: p.name
)
def test_every_shipped_office_draws(office_dir):
    """Forty offices, and any one of them may be the first a student
    asks to see."""
    diagram = draw_office_dir(office_dir)
    assert diagram.startswith("flowchart LR")

    spec = parse_office_dir(office_dir)
    declared = (
        {s.name for s in spec.sources}
        | {k.name for k in spec.sinks}
        | {a.agent_name for a in spec.agents}
    )
    drawn = _node_ids(diagram)
    missing = declared - drawn
    assert not missing, f"{office_dir.name}: not drawn: {sorted(missing)}"
