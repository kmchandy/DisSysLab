"""``dsl draw``: an office as a list of arrows, or as a Mermaid diagram.

The office file already names both ends of every arrow, so the text form
adds two things it does not say in one place: what kind each name is,
and what is connected to nothing. The Mermaid form is a picture, worth
having exactly where an office branches -- a fan-out into a fan-in reads
poorly as lines and well as a drawing. Paste it into GitHub or any
Markdown viewer that renders Mermaid.

Drawn on request, not after every edit, so the layout need not stay
stable under change; Mermaid lays it out.

It says nothing about behaviour. Two offices with the same picture can
differ in every way that matters at run time; a structurally perfect
diagram can stall. The picture is an aid to reading the wiring, not
evidence about it.
"""

from __future__ import annotations

from pathlib import Path

from dissyslab.office.model import Connection, Declaration, OfficeFile, PortRef
from dissyslab.office.syntax import parse_office_file

#: Words Mermaid reads as syntax where a node id may appear.
_MERMAID_RESERVED = {
    "end", "graph", "subgraph", "flowchart", "class", "classDef",
    "click", "style", "linkStyle", "direction",
}


def _end(ref: PortRef) -> str:
    return f"{ref.name}.{ref.port}" if ref.port else ref.name


def unconnected(office: OfficeFile) -> list[str]:
    """Names that nothing feeds or that feed nothing, where that matters."""
    senders = {c.sender.name for c in office.connections}
    receivers = {c.receiver.name for c in office.connections}
    lines: list[str] = []
    for d in office.sources:
        if d.name not in senders:
            lines.append(f"{d.name} (source) sends to nothing")
    for d in office.sinks:
        if d.name not in receivers:
            lines.append(f"{d.name} (sink) receives nothing")
    for d in office.agents:
        if d.name not in receivers and d.kind != "office":
            lines.append(f"{d.name} ({d.kind}) receives nothing")
        if d.name not in senders and d.kind != "office":
            lines.append(f"{d.name} ({d.kind}) sends to nothing")
    return lines


def text(office: OfficeFile, name: str = "office") -> str:
    """Every declaration with its kind, every arrow, then what is unconnected."""
    width = max((len(d.name) for d in office.declarations), default=0)
    out = [f"{name}"]
    for section, decls in (("sources", office.sources), ("sinks", office.sinks),
                           ("agents", office.agents)):
        if decls:
            out.append(f"  {section}:")
            out += [f"    {d.name.ljust(width)}  {d.kind}" for d in decls]
    if office.connections:
        out.append("  arrows:")
        out += [f"    {_end(c.sender)} -> {_end(c.receiver)}" for c in office.connections]
    loose = unconnected(office)
    if loose:
        out.append("  connected to nothing:")
        out += [f"    {line}" for line in loose]
    return "\n".join(out)


def _node_id(name: str) -> str:
    return f"n_{name}" if name in _MERMAID_RESERVED else name


def _node(d: Declaration) -> str:
    label = d.name if d.kind == d.name else f"{d.name}<br/><i>{d.kind}</i>"
    i = _node_id(d.name)
    if d.section == "sources":
        return f'    {i}(["{label}"])'
    if d.section == "sinks":
        return f'    {i}[["{label}"]]'
    if d.kind == "router":
        return f'    {i}{{{{"{label}"}}}}'
    if d.kind in ("synchronizer", "gate"):
        return f'    {i}[/"{label}"\\]'
    if d.kind == "unassigned":
        return f'    {i}["{label}"]:::draft'
    return f'    {i}["{label}"]'


def _edge(c: Connection) -> str:
    ports = [p for p in (c.sender.port, c.receiver.port) if p]
    label = f"|{' / '.join(ports)}|" if ports else ""
    return f"    {_node_id(c.sender.name)} -->{label} {_node_id(c.receiver.name)}"


def mermaid(office: OfficeFile) -> str:
    """A Mermaid flowchart: sources round, sinks boxed twice, routers hexagons."""
    lines = ["flowchart LR"]
    for name in office.inputs + office.outputs:
        lines.append(f'    {_node_id(name)}(("{name}"))')
    lines += [_node(d) for d in office.declarations]
    lines += [_edge(c) for c in office.connections]
    if any(d.kind == "unassigned" for d in office.agents):
        lines.append("    classDef draft stroke-dasharray: 5 5")
    return "\n".join(lines)


def fenced(diagram: str) -> str:
    """The diagram inside a ```mermaid fence, ready to paste into Markdown."""
    return f"```mermaid\n{diagram}\n```"


def text_office_dir(office_dir: Path) -> str:
    return text(parse_office_file(office_dir / "office.md"), office_dir.resolve().name)


def draw_office_dir(office_dir: Path) -> str:
    return mermaid(parse_office_file(office_dir / "office.md"))
