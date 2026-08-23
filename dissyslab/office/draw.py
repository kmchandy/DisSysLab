"""Draw an office as a Mermaid diagram.

Why this exists
---------------
``office.md`` is the program and the record of what was built, and it
reads well for a handful of agents. It stops reading well at the point
an office branches: seven agents and eleven connection lines describe a
fan-out into a fan-in perfectly and show it not at all. A picture is
worth having exactly there.

It is produced **on request** -- ``dsl draw``, or "draw the network"
addressed to an assistant -- and not on every change. That decision is
what lets this module stay simple. A diagram shown after every edit
would have to be stable under change, so that adding an agent did not
rearrange the ones already on the screen and force the reader to find
them again; laying out a graph under that constraint is a real problem.
A diagram asked for once, and read once, has no such obligation.

What it draws, and what it does not
-----------------------------------
The graph, faithfully: every source, sink and agent named in the spec,
every connection, and the outbox and inbox names on an edge wherever
they are not the defaults. It draws an *incomplete* office too -- a
name that appears in ``Connections:`` and is declared nowhere gets a
node of its own, marked, because an office you cannot run is when you
most want to look at it.

It says nothing about behaviour. Two offices with the same picture can
differ in every way that matters at run time, and the boundary between
what a graph can show and what it cannot is the same boundary
``check_wiring`` runs into: a structurally perfect diagram can deadlock.
The picture is an aid to reading the wiring, not evidence about it.
"""
from __future__ import annotations

from pathlib import Path

# Mermaid parses these as syntax wherever a node id may appear, so an
# agent called `end` would silently break the diagram rather than
# failing loudly. Agent names come from the user; this list is short
# and cheap insurance.
_RESERVED = {
    "end", "graph", "subgraph", "flowchart", "class", "classDef",
    "click", "style", "linkStyle", "direction",
}

# Ports the user did not choose. Naming these on an edge adds a word to
# every arrow and tells the reader nothing they could act on.
_DEFAULT_OUT_PORTS = {"out", "destination"}
_DEFAULT_IN_PORTS = {"in_", "in"}

# A role that is present in the file but not yet decided. Drawn dashed,
# so that the shape of a half-built office is legible at a glance.
_UNASSIGNED = {None, "unassigned", "placeholder"}


def _node_id(name: str) -> str:
    """A Mermaid-safe id for an office name.

    Office names are already Python-style identifiers, so the only
    hazard is a collision with Mermaid's own keywords.
    """
    return f"{name}_" if name in _RESERVED else name


def _escape(text: str) -> str:
    """Make a label safe inside Mermaid's square brackets."""
    return text.replace('"', "&quot;").replace("[", "(").replace("]", ")")


def _edge_label(out_port: str, in_port: str) -> str | None:
    """The part of an edge worth naming.

    An agent that routes to ``worth_a_look`` and ``too_senior`` is
    doing the most interesting thing in the office, and which arrow is
    which is the whole question. An agent with one unnamed output is
    not, and labelling it as ``out`` is noise.
    """
    out_named = out_port not in _DEFAULT_OUT_PORTS
    in_named = in_port not in _DEFAULT_IN_PORTS
    if out_named and in_named:
        return f"{out_port} → {in_port}"
    if out_named:
        return out_port
    if in_named:
        # The arrow already says "into"; an arrow labelled "→ entities"
        # says it twice.
        return in_port
    return None


def draw_spec(spec) -> str:
    """Render an OfficeSpec as a Mermaid ``flowchart LR`` block.

    Deterministic: nodes appear in the order the office declares them
    and edges in the order the connections are written, so the same
    office always produces the same text and a diff of two drawings is
    a diff of two offices.
    """
    lines: list[str] = ["flowchart LR"]

    source_names = [s.name for s in spec.sources]
    sink_names = [k.name for k in spec.sinks]
    agents = [(a.agent_name, a.role_name, a.path) for a in spec.agents]
    declared: set[str] = set(source_names) | set(sink_names) | {a[0] for a in agents}

    # Names used in Connections: that nothing declares. An office in
    # this state does not compile; drawing it anyway is the point.
    undeclared: list[str] = []
    for conn in spec.connections:
        for endpoint in (conn.source, *conn.destinations):
            if endpoint.name not in declared and endpoint.name not in undeclared:
                undeclared.append(endpoint.name)

    classes: dict[str, list[str]] = {
        "src": [], "sink": [], "draft": [], "sub": [], "unknown": [],
    }

    for name in source_names:
        lines.append(f"  {_node_id(name)}[{_escape(name)}]")
        classes["src"].append(_node_id(name))

    for agent_name, role_name, path in agents:
        node = _node_id(agent_name)
        if role_name in _UNASSIGNED:
            lines.append(f"  {node}[{_escape(agent_name)}<br/>no role yet]")
            classes["draft"].append(node)
        elif path is not None:
            lines.append(f"  {node}[{_escape(agent_name)}<br/>office: {_escape(path)}]")
            classes["sub"].append(node)
        else:
            lines.append(f"  {node}[{_escape(agent_name)}<br/>{_escape(role_name)}]")

    for name in sink_names:
        lines.append(f"  {_node_id(name)}[{_escape(name)}]")
        classes["sink"].append(_node_id(name))

    for name in undeclared:
        lines.append(f"  {_node_id(name)}[{_escape(name)}<br/>not declared]")
        classes["unknown"].append(_node_id(name))

    for conn in spec.connections:
        sender = _node_id(conn.source.name)
        for dest in conn.destinations:
            label = _edge_label(conn.source.port, dest.port)
            arrow = f"-->|{label}|" if label else "-->"
            lines.append(f"  {sender} {arrow} {_node_id(dest.name)}")

    styles = {
        "src": "fill:#dbeafe,stroke:#1d4ed8",
        "sink": "fill:#fef3c7,stroke:#92400e",
        "draft": "fill:#f3f4f6,stroke:#9ca3af,stroke-dasharray:4 3",
        "sub": "fill:#ede9fe,stroke:#6d28d9",
        "unknown": "fill:#fee2e2,stroke:#b91c1c,stroke-dasharray:4 3",
    }
    for kind, members in classes.items():
        if members:
            lines.append(f"  classDef {kind} {styles[kind]}")
            lines.append(f"  class {','.join(members)} {kind}")

    return "\n".join(lines)


def draw_office_dir(office_dir: Path) -> str:
    """Parse the office at ``office_dir`` and render it."""
    from dissyslab.office.parser import parse_office_dir

    return draw_spec(parse_office_dir(Path(office_dir)))


def fenced(diagram: str) -> str:
    """Wrap a diagram in a Markdown mermaid fence.

    GitHub, and several editors, render this where they would show a
    bare diagram as text.
    """
    return f"```mermaid\n{diagram}\n```"
