"""From an office folder to a running network (spec section 8).

``build_office(folder)`` does, in order, the steps spec section 8 lists,
and nothing else:

1. parse ``office.md`` (:mod:`dissyslab.office.syntax`);
2. find what every kind refers to (:mod:`dissyslab.office.resolve`);
   every problem is reported together, with its line, before anything is
   built;
3. build each source and sink -- a built-in one through the component
   registry, a local one from the office's ``sources/`` or ``sinks/``
   folder (one class, constructed with its arguments);
4. build each role as an annotator or author agent
   (:mod:`dissyslab.agents`): an English role from its text and ``ai=``,
   a Python role from its one class and its arguments;
5. connect them, one runtime connection per arrow.

``run_office(folder)`` builds and runs, from inside the office folder so
that relative paths in the office file mean what they say, and returns
the exit code: 0 when every message was handled, 1 otherwise.

**Being built (Phase 3).** Coordinators, nested offices and drafts are
not built yet; an office that uses one gets a clear "not built
yet" error naming the line, never a guess.
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from dissyslab.agents.english import english_call
from dissyslab.agents.python_role import python_instance
from dissyslab.agents.role_agent import role_agent
from dissyslab.agents.router import RouterAgent
from dissyslab.office.frontmatter import read_front_matter
from dissyslab.office.model import Connection, Declaration, OfficeFile
from dissyslab.office.resolve import Found, resolve_office
from dissyslab.office.syntax import parse_office_file
from dissyslab.runtime.agent import Agent
from dissyslab.runtime.network import Network

#: The runtime's names for a role's, source's and sink's single ports.
RUNTIME_OUT = "out_"
RUNTIME_IN = "in_"


class BuildError(Exception):
    """An office that cannot be built, with every reason found."""


# ── Sources and sinks ──────────────────────────────────────────────────────


def _builtin_component(decl: Declaration) -> Agent:
    """A registry source or sink, built by the existing component code."""
    from dissyslab.office.compiler import _build_sink, _build_source
    from dissyslab.office.office_spec import SinkSpec, SourceSpec

    args = tuple(decl.args.items())
    block: Agent
    if decl.section == "sources":
        block = _build_source(SourceSpec(name=decl.kind, args=args))
    else:
        block = _build_sink(SinkSpec(name=decl.kind, args=args))
    return block


def _local_component(decl: Declaration, found: Found) -> Agent:
    """A source or sink from the office's own folder: one class.

    A local source's instance is called with no arguments and returns the
    next message, or None when it has no more. A local sink's instance is
    called with each message.
    """
    from dissyslab.blocks import Sink, Source

    assert found.path is not None
    instance = python_instance(found.path, read_front_matter(found.path), dict(decl.args))
    if not callable(instance):
        raise BuildError(f"line {decl.line}: {found.path.name}'s class has no __call__.")
    block: Agent
    if decl.section == "sources":
        block = Source(fn=instance, name=decl.name)
    else:
        block = Sink(fn=instance, name=decl.name)
    return block


# ── Agents ─────────────────────────────────────────────────────────────────


def _role(decl: Declaration, found: Found) -> Agent:
    assert found.path is not None
    fm = read_front_matter(found.path)
    args: dict[str, Any] = dict(decl.args)
    if found.language == "english":
        ai = args.pop("ai", None)
        if args:
            raise BuildError(
                f"line {decl.line}: an English role takes only ai=, not "
                f"{', '.join(args)} (spec 4.2)."
            )
        return role_agent(decl.name, english_call(fm, ai=ai), fm)
    instance = python_instance(found.path, fm, args)
    if not callable(instance):
        raise BuildError(f"line {decl.line}: {found.path.name}'s class has no __call__.")
    return role_agent(decl.name, instance, fm)


def _router(decl: Declaration, office: OfficeFile) -> Agent:
    """A router; its outboxes are the values its connections name (spec 5)."""
    args = dict(decl.args)
    on = args.pop("on", None)
    if not isinstance(on, str) or not on:
        raise BuildError(
            f"line {decl.line}: every router names its field: {decl.name}: router(on=\"...\")."
        )
    if args:
        raise BuildError(f"line {decl.line}: a router takes only on=, not {', '.join(args)}.")
    outboxes: list[str] = []
    for c in office.connections:
        if c.sender.name != decl.name:
            continue
        if c.sender.port is None:
            raise BuildError(
                f"line {c.line}: a router's outboxes are named by values: write "
                f"{decl.name}.<value> -> {c.receiver}."
            )
        if c.sender.port not in outboxes:
            outboxes.append(c.sender.port)
    if not outboxes:
        raise BuildError(f"line {decl.line}: router {decl.name} sends nowhere.")
    return RouterAgent(name=decl.name, on=on, outboxes=outboxes)


def _gate(decl: Declaration) -> Agent:
    """A gate (spec 6): admits one item from ``in``, then waits for ``done``.

    The runtime's existing ``Gate`` coordinator, unchanged; it already
    tells the termination detector which inbox it is waiting on.
    """
    from dissyslab.blocks.gate import Gate

    if decl.args:
        raise BuildError(f"line {decl.line}: a gate takes no arguments.")
    gate: Agent = Gate(name=decl.name)
    return gate


def _agent(decl: Declaration, found: Found, office: OfficeFile) -> Agent:
    if found.origin == "reserved":
        if found.kind == "router":
            return _router(decl, office)
        if found.kind == "gate":
            return _gate(decl)
        if found.kind == "unassigned":
            raise BuildError(
                f"line {decl.line}: {decl.name} is unassigned; a draft office can be "
                "checked and drawn, but not run (spec 3.5)."
            )
        raise BuildError(f"line {decl.line}: {found.kind} is not built yet (Phase 3).")
    return _role(decl, found)


# ── Connections ────────────────────────────────────────────────────────────


#: Inboxes by kind, as written in the office file -> the runtime's name.
#: Anything not listed has the one inbox ``in``.
INBOXES: dict[str, dict[str, str]] = {
    "gate": {"in": RUNTIME_IN, "done": "done"},
}


def _runtime_connection(c: Connection, found: dict[str, Found]) -> tuple[str, str, str, str]:
    """One arrow as the runtime's (sender, outbox, receiver, inbox).

    A router's outbox is the value after the dot. Every other sender has
    one outbox, ``out``. A receiver's inboxes are ``in``, or for a gate
    ``in`` and ``done``. A port that does not exist is an error naming the
    arrow (spec 3.3).
    """
    sender, receiver = found[c.sender.name], found[c.receiver.name]
    if sender.kind == "router":
        out_port = c.sender.port or ""  # _router has already required a value
    elif c.sender.port in (None, "out"):
        out_port = RUNTIME_OUT
    else:
        raise BuildError(
            f"line {c.line}: {c.sender.name} has one outbox, out; it has no "
            f"{c.sender.port!r} (spec 3.3)."
        )
    inboxes = INBOXES.get(receiver.kind, {"in": RUNTIME_IN}) if receiver.origin == "reserved" \
        else {"in": RUNTIME_IN}
    written_in = c.receiver.port or "in"
    if written_in not in inboxes:
        names = " and ".join(inboxes)
        raise BuildError(
            f"line {c.line}: {c.receiver.name} has inbox{'es' if len(inboxes) > 1 else ''} "
            f"{names}; it has no {written_in!r} (spec 3.3)."
        )
    return (c.sender.name, out_port, c.receiver.name, inboxes[written_in])


# ── The office ─────────────────────────────────────────────────────────────


def build_network(office: OfficeFile, office_dir: Path) -> Network:
    """Build the runtime network for a parsed office."""
    if office.inputs or office.outputs:
        raise BuildError("nested offices (inputs:, outputs:) are not built yet (Phase 3).")

    found, problems = resolve_office(office, office_dir)
    if problems:
        raise BuildError("\n".join(f"line {p.line}: {p.message}" for p in problems))

    blocks: dict[str, Agent | Network] = {}
    for decl in office.sources + office.sinks:
        f = found[decl.name]
        blocks[decl.name] = (
            _local_component(decl, f) if f.origin == "local" else _builtin_component(decl)
        )
    for decl in office.agents:
        blocks[decl.name] = _agent(decl, found[decl.name], office)

    connections = [_runtime_connection(c, found) for c in office.connections]
    return Network(name=office_dir.name, blocks=blocks, connections=connections)


@contextmanager
def inside(office_dir: Path) -> Iterator[None]:
    """Work from inside the office folder, so relative paths mean what they say."""
    before = os.getcwd()
    os.chdir(office_dir)
    try:
        yield
    finally:
        os.chdir(before)


def build_office(office_dir: Path) -> Network:
    """Parse, resolve and build the office in ``office_dir``.

    Built from inside the folder: a component that opens
    ``path="articles.jsonl"`` opens the office's own file.
    """
    office_dir = office_dir.resolve()
    with inside(office_dir):
        office = parse_office_file(office_dir / "office.md")
        return build_network(office, office_dir)


def run_office(office_dir: Path) -> int:
    """Build and run the office from inside its folder; return the exit code."""
    office_dir = office_dir.resolve()
    with inside(office_dir):
        return build_office(office_dir).run_network()
