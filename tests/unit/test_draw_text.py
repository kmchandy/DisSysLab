"""`dsl draw` as text: both ends of every edge, and what is unconnected.

The question this answers is one `office.md` cannot. `Screen is a
relevance_filter.` says nothing about Screen having an outbox called
`discard`; the reader must open a role file that may not even be in her
folder and apply a regular expression to prose in her head.

So the listing names both ports on every edge, and every declared port
appears exactly once -- on an edge, or in the block of things that go
nowhere. That second block is the same set of facts `dsl check` reports
as W1, W2 and W8, said as a shape rather than as findings.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from dissyslab.office.draw import text_office_dir

_FILTER = """---
emits: keeps some items
outboxes: keep, discard
---
# Role: my_filter

If the item is relevant, send to keep. Otherwise send to discard.
"""


def _office(tmp_path: Path, body: str, roles: dict | None = None) -> Path:
    d = tmp_path / "office"
    (d / "roles").mkdir(parents=True, exist_ok=True)
    (d / "office.md").write_text(body, encoding="utf-8")
    for name, text in (roles or {}).items():
        (d / "roles" / name).write_text(text, encoding="utf-8")
    return d


_WIRED = """# Office: x

Sources: starter
Sinks: console_printer, discard

Agents:
Screen is a my_filter.

Connections:
starter's destination is Screen.
Screen's keep is console_printer.
Screen's discard is discard.
"""


# ── the edges ─────────────────────────────────────────────────────────


def test_both_ports_are_named_on_every_edge(tmp_path):
    """Including the defaults. The Mermaid rendering suppresses `out`
    and `in_` because a label on every arrow is noise in a picture; in
    a table the column is there anyway, and a reader learning the model
    is helped by seeing that a source's outbox really is called
    `destination`."""
    out = text_office_dir(_office(tmp_path, _WIRED, {"my_filter.md": _FILTER}))
    assert "starter" in out and "destination" in out and "in_" in out
    for line in out.splitlines():
        if "starter" in line:
            assert line.index("destination") < line.index("in_"), (
                "the sending port must come before the receiving one"
            )
            break


def test_every_connection_appears(tmp_path):
    out = text_office_dir(_office(tmp_path, _WIRED, {"my_filter.md": _FILTER}))
    edges = [ln for ln in out.splitlines() if "──▶" in ln and "nothing" not in ln]
    assert len(edges) == 3


def test_an_office_with_no_connections_says_so(tmp_path):
    d = _office(tmp_path, "# Office: x\n\nAgents:\nA is unassigned.\n")
    assert "(no connections yet)" in text_office_dir(d)


# ── what is unconnected ───────────────────────────────────────────────


def test_an_unwired_outbox_is_listed(tmp_path):
    """The case that motivated the whole thing: `discard` exists,
    nothing says so in office.md, and an unwired outbox stops the run
    the first time it is used."""
    body = _WIRED.replace("Screen's discard is discard.\n", "").replace(
        ", discard", ""
    )
    out = text_office_dir(_office(tmp_path, body, {"my_filter.md": _FILTER}))
    assert "Not connected:" in out
    assert "Screen's discard" in out
    assert "nothing" in out


def test_a_sink_nothing_feeds_is_listed(tmp_path):
    body = _WIRED.replace("Screen's keep is console_printer.\n", "")
    out = text_office_dir(_office(tmp_path, body, {"my_filter.md": _FILTER}))
    assert "console_printer's in_" in out


def test_a_source_with_no_destination_is_listed(tmp_path):
    body = _WIRED.replace("starter's destination is Screen.\n", "")
    out = text_office_dir(_office(tmp_path, body, {"my_filter.md": _FILTER}))
    assert "starter's destination" in out


def test_nothing_is_listed_when_everything_is_wired(tmp_path):
    out = text_office_dir(_office(tmp_path, _WIRED, {"my_filter.md": _FILTER}))
    assert "Not connected:" not in out


def test_an_undecided_agent_is_named(tmp_path):
    body = _WIRED.replace(
        "Screen is a my_filter.", "Screen is a my_filter.\nLater is unassigned."
    )
    out = text_office_dir(_office(tmp_path, body, {"my_filter.md": _FILTER}))
    assert "No role yet: Later" in out


# ── the two renderings agree ──────────────────────────────────────────


def test_the_two_renderings_describe_the_same_edges(tmp_path):
    """Text and Mermaid come from one spec. If they ever disagreed
    about the graph, neither could be believed -- the same reason the
    W2 check calls the loader's own port extractor rather than its own
    idea of one."""
    from dissyslab.office.draw import draw_office_dir

    d = _office(tmp_path, _WIRED, {"my_filter.md": _FILTER})
    text = text_office_dir(d)
    mermaid = draw_office_dir(d)

    text_edges = len([ln for ln in text.splitlines()
                      if "──▶" in ln and "nothing" not in ln])
    mermaid_edges = len([ln for ln in mermaid.splitlines() if "-->" in ln])
    assert text_edges == mermaid_edges


# ── the whole gallery renders ─────────────────────────────────────────


GALLERY = Path(__file__).resolve().parents[2] / "dissyslab" / "gallery"
OFFICES = sorted(p.parent for p in GALLERY.rglob("office.md"))


@pytest.mark.parametrize("office", OFFICES, ids=[d.name for d in OFFICES])
def test_every_shipped_office_draws(office):
    """A drawing is what someone asks for when an office confuses them,
    so it has to survive every office we ship -- including the one
    marked work-in-progress, whose sources are not registered."""
    out = text_office_dir(office)
    assert out and "──▶" in out or "(no connections yet)" in out


# ── where a run writes ────────────────────────────────────────────────


def test_a_packaged_office_does_not_chdir_into_site_packages(tmp_path):
    """`dsl run periodic_brief` used to write brief.html *inside the
    installed package*, because the generated artifact chdir's to the
    office so that relative paths resolve beside it. That is right for
    an office she copied with `dsl init` and wrong for one that is part
    of the library: "beside the office" is then site-packages, and her
    brief lands somewhere she cannot find and did not ask to be written
    to.

    The artifact decides for itself rather than trusting a flag from
    `dsl run`, so `python build/run.py` behaves the same way.
    """
    from dissyslab.office.cli_helpers import emit_run_py

    d = _office(tmp_path, _WIRED, {"my_filter.md": _FILTER})
    source = Path(emit_run_py(d)).read_text(encoding="utf-8")

    assert "os.chdir" in source, "an office of her own must still chdir"
    assert "_pkg not in _HERE.parents" in source, (
        "the chdir must be skipped when the office is the installed "
        "package; without the guard a gallery office writes into "
        "site-packages"
    )
