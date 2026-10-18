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

A draft (an ``unassigned`` agent) is not run: it gets a clear error
naming the line (spec 3.5).
"""

from __future__ import annotations

import os
import sys
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator

from dissyslab.agents.english import english_call
from dissyslab.agents.python_role import python_instance
from dissyslab.agents.role_agent import role_agent
from dissyslab.agents.router import RouterAgent
from dissyslab.agents.synchronizer import SynchronizerAgent
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
    """A source or sink from the component registry (:mod:`dissyslab.office.components`)."""
    from dissyslab.office.components import ComponentError, build_component

    try:
        return build_component(decl)
    except ComponentError as exc:
        raise BuildError(f"line {decl.line}: {exc}") from None


def _local_component(decl: Declaration, found: Found) -> Agent:
    """A source or sink from the office's own folder: one class.

    A local source's instance is called with no arguments and returns the
    next message, or None when it has no more. A local sink's instance is
    called with each message, after the message is checked against the
    sink's ``in:`` if it declares one (:mod:`dissyslab.agents.checked_sink`).
    """
    from dissyslab.agents.checked_sink import sink_agent
    from dissyslab.blocks import Source

    assert found.path is not None
    fm = read_front_matter(found.path)
    instance = python_instance(found.path, fm, dict(decl.args))
    if not callable(instance):
        raise BuildError(f"line {decl.line}: {found.path.name}'s class has no __call__.")
    block: Agent
    if decl.section == "sources":
        block = Source(fn=instance, name=decl.name)
    else:
        block = sink_agent(fn=instance, name=decl.name, front_matter=fm)
    return block


# ── Agents ─────────────────────────────────────────────────────────────────


def english_args_problem(decl: Declaration) -> str | None:
    """The problem with an English role's arguments, or None.

    It takes only ``ai=``, and that must name a backend
    (``dissyslab.backends.backend_names``, which includes any registered
    through ``DSL_BACKEND_MODULE``).
    """
    import difflib

    from dissyslab.backends import backend_names

    others = [k for k in decl.args if k != "ai"]
    if others:
        return (
            f"line {decl.line}: an English role takes only ai=, not "
            f"{', '.join(others)}. See `dsl grammar roles`."
        )
    ai = decl.args.get("ai")
    if ai is None:
        return None
    names = backend_names()
    if not isinstance(ai, str) or ai.lower() not in names:
        near = difflib.get_close_matches(str(ai).lower(), names, n=1)
        hint = f" Did you mean {near[0]!r}?" if near else ""
        return (
            f"line {decl.line}: ai={ai!r} is not a model backend.{hint} "
            "docs/LANGUAGE_MODELS.md lists them."
        )
    return None


def _role(decl: Declaration, found: Found) -> Agent:
    assert found.path is not None
    fm = read_front_matter(found.path)
    args: dict[str, Any] = dict(decl.args)
    if found.language == "english":
        problem = english_args_problem(decl)
        if problem:
            raise BuildError(problem)
        return role_agent(decl.name, english_call(fm, ai=args.get("ai")), fm)
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


def _synchronizer(decl: Declaration, office: OfficeFile) -> Agent:
    """A keyed synchronizer (spec 6); its inboxes are the names its connections use."""
    args = dict(decl.args)
    on = args.pop("on", None)
    collect = args.pop("collect", None)
    if not isinstance(on, str) or not on:
        raise BuildError(
            f"line {decl.line}: every synchronizer names its key: "
            f"{decl.name}: synchronizer(on=\"...\")."
        )
    if collect is not None and not isinstance(collect, str):
        raise BuildError(f"line {decl.line}: collect= is the name of a field, in quotes.")
    if args:
        raise BuildError(
            f"line {decl.line}: a synchronizer takes on= and collect=, not {', '.join(args)}."
        )
    for c in office.connections:
        if c.receiver.name == decl.name and c.receiver.port is None:
            raise BuildError(
                f"line {c.line}: a synchronizer's inboxes are named by its connections: "
                f"write {c.sender} -> {decl.name}.<inbox>."
            )
    inboxes = office.inboxes_of(decl.name)
    if len(inboxes) < 2:
        raise BuildError(
            f"line {decl.line}: synchronizer {decl.name} needs at least two inboxes; "
            f"it has {', '.join(inboxes) or 'none'}."
        )
    return SynchronizerAgent(name=decl.name, on=on, inboxes=inboxes, collect=collect)


def _agent(decl: Declaration, found: Found, office: OfficeFile) -> Agent:
    if found.origin == "reserved":
        if found.kind == "router":
            return _router(decl, office)
        if found.kind == "gate":
            return _gate(decl)
        if found.kind == "synchronizer":
            return _synchronizer(decl, office)
        if found.kind == "unassigned":
            raise BuildError(
                f"line {decl.line}: {decl.name} is unassigned; a draft office can be "
                "checked and drawn, but not run. Give it a role first."
            )
        raise BuildError(f"line {decl.line}: {found.kind} is not built yet (Phase 3).")
    return _role(decl, found)


# ── Connections ────────────────────────────────────────────────────────────


#: Inboxes by kind, as written in the office file -> the runtime's name.
#: Anything not listed has the one inbox ``in``.
INBOXES: dict[str, dict[str, str]] = {
    "gate": {"in": RUNTIME_IN, "done": "done"},
}


#: The runtime's name for the outside of a network, in a nested office.
EXTERNAL = "external"


@dataclass
class _Ports:
    """What the connections of one office may name, beyond ``in`` and ``out``."""

    found: dict[str, Found]
    inputs: tuple[str, ...]
    outputs: tuple[str, ...]
    #: For each nested office used as an agent: (its inputs, its outputs).
    nested: dict[str, tuple[tuple[str, ...], tuple[str, ...]]] = field(default_factory=dict)


def _sender(c: Connection, p: _Ports) -> tuple[str, str]:
    name, port = c.sender.name, c.sender.port
    if name in p.inputs:  # inside a nested office, an input acts as a source (spec 3.4)
        if port not in (None, "out"):
            raise BuildError(f"line {c.line}: input {name} has one outbox, out.")
        return EXTERNAL, name
    if name in p.nested:
        outs = p.nested[name][1]
        if port not in outs:
            raise BuildError(
                f"line {c.line}: office {name}'s outputs are {', '.join(outs) or 'none'}; "
                f"write {name}.<output> -> {c.receiver}. See `dsl grammar`, Nested offices."
            )
        return name, port
    if p.found[name].kind == "router":
        return name, port or ""  # _router has already required a value
    if port in (None, "out"):
        return name, RUNTIME_OUT
    raise BuildError(
        f"line {c.line}: {name} has one outbox, out; it has no {port!r}. See `dsl grammar`, Ports."
    )


def _receiver(c: Connection, p: _Ports) -> tuple[str, str]:
    name, port = c.receiver.name, c.receiver.port
    if name in p.outputs:  # inside a nested office, an output acts as a sink (spec 3.4)
        if port not in (None, "in"):
            raise BuildError(f"line {c.line}: output {name} has one inbox, in.")
        return EXTERNAL, name
    if name in p.nested:
        ins = p.nested[name][0]
        if port not in ins:
            raise BuildError(
                f"line {c.line}: office {name}'s inputs are {', '.join(ins) or 'none'}; "
                f"write {c.sender} -> {name}.<input>. See `dsl grammar`, Nested offices."
            )
        return name, port
    found = p.found[name]
    written_in = port or "in"
    if found.kind == "synchronizer":
        return name, written_in
    inboxes = INBOXES.get(found.kind, {"in": RUNTIME_IN}) if found.origin == "reserved" \
        else {"in": RUNTIME_IN}
    if written_in not in inboxes:
        names = " and ".join(inboxes)
        raise BuildError(
            f"line {c.line}: {name} has inbox{'es' if len(inboxes) > 1 else ''} "
            f"{names}; it has no {written_in!r}. See `dsl grammar`, Ports."
        )
    return name, inboxes[written_in]


def _runtime_connection(c: Connection, p: _Ports) -> tuple[str, str, str, str]:
    """One arrow as the runtime's (sender, outbox, receiver, inbox).

    A router's outbox is the value after the dot; every other agent has
    one outbox, ``out``. A receiver's inboxes are ``in``, or for a gate
    ``in`` and ``done``, or for a synchronizer the names its connections
    use. A nested office's ports are its declared inputs and outputs, and
    inside it those act as a source and a sink. A port that does not
    exist is an error naming the arrow (spec 3.3, 3.4).
    """
    return _sender(c, p) + _receiver(c, p)


# ── The office ─────────────────────────────────────────────────────────────


def _nested_office(
    decl: Declaration, office_dir: Path, stack: tuple[Path, ...]
) -> Network:
    """``name: office(path="...")``: build the office in that folder. See `dsl grammar`, Nested offices."""
    args = dict(decl.args)
    rel = args.pop("path", None)
    if not isinstance(rel, str) or args:
        raise BuildError(
            f"line {decl.line}: a nested office is {decl.name}: office(path=\"<folder>\")."
        )
    sub_dir = (office_dir / rel).resolve()
    if not (sub_dir / "office.md").is_file():
        raise BuildError(f"line {decl.line}: there is no office.md in {sub_dir}.")
    if sub_dir in stack:
        raise BuildError(f"line {decl.line}: {sub_dir.name} contains itself.")
    with inside(sub_dir):
        sub = parse_office_file(sub_dir / "office.md")
        if not sub.inputs and not sub.outputs:
            raise BuildError(
                f"line {decl.line}: {sub_dir.name} has no inputs: or outputs:, so it "
                "cannot be part of another office."
            )
        return build_network(sub, sub_dir, name=decl.name, stack=stack + (sub_dir,))


def build_network(
    office: OfficeFile,
    office_dir: Path,
    *,
    name: str | None = None,
    stack: tuple[Path, ...] = (),
) -> Network:
    """Build the runtime network for a parsed office (and the offices it nests)."""
    found, problems = resolve_office(office, office_dir)
    if problems:
        raise BuildError("\n".join(f"line {p.line}: {p.message}" for p in problems))
    drafts = [d for d in office.agents if found[d.name].kind == "unassigned"]
    if drafts:
        # Refused before anything is built: a draft is not run, so no
        # source should open a file or a feed on its way to being refused.
        raise BuildError("\n".join(
            f"line {d.line}: {d.name} is unassigned; a draft office can be "
            "checked and drawn, but not run. Give it a role first." for d in drafts))

    ports = _Ports(found=found, inputs=office.inputs, outputs=office.outputs)
    blocks: dict[str, Agent | Network] = {}
    for decl in office.sources + office.sinks:
        f = found[decl.name]
        blocks[decl.name] = (
            _local_component(decl, f) if f.origin == "local" else _builtin_component(decl)
        )
    for decl in office.agents:
        if found[decl.name].kind == "office":
            sub = _nested_office(decl, office_dir, stack or (office_dir.resolve(),))
            ports.nested[decl.name] = (tuple(sub.inports), tuple(sub.outports))
            blocks[decl.name] = sub
        else:
            blocks[decl.name] = _agent(decl, found[decl.name], office)

    connections = [_runtime_connection(c, ports) for c in office.connections]
    return Network(
        name=name or office_dir.name,
        blocks=blocks,
        connections=connections,
        inports=list(office.inputs),
        outports=list(office.outputs),
    )


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
        if office.inputs or office.outputs:
            raise BuildError(
                f"{office_dir.name} has inputs: or outputs:, so it is meant to sit inside "
                "another office (name: office(path=...)); run that office instead."
            )
        return build_network(office, office_dir)


#: The exit status of a run stopped with Ctrl-C (128 + SIGINT, by convention).
STOPPED = 130


def run_office(office_dir: Path) -> int:
    """Build and run the office from inside its folder; return the exit code.

    An office with a live source (a news feed, a webhook, a mailbox) runs
    until it is stopped. Ctrl-C stops it: every agent is asked to stop, the
    run summary is printed (when ``DSL_RUN_SUMMARY`` is set, as ``dsl run``
    sets it), and ``STOPPED`` is returned. Agents still busy -- a source in
    the middle of a network call cannot notice a stop request -- are named.
    The caller must not wait for their threads: ``dsl run`` exits at once.
    """
    office_dir = office_dir.resolve()
    with inside(office_dir):
        network = build_office(office_dir)
        try:
            return network.run_network()
        except KeyboardInterrupt:
            print("\nStopped (Ctrl-C).", file=sys.stderr, flush=True)
            still_running = network._stop_all_agents()
            if os.environ.get("DSL_RUN_SUMMARY"):
                network.print_run_summary()
            if still_running:
                names = ", ".join(t.name.replace("_thread", "") for t in still_running)
                print(f"  (still busy when stopped: {names})", file=sys.stderr)
            return STOPPED
