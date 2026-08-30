"""Static wiring checks for an office.

What this is for
----------------
The existing validation is **local**: the parser reports syntax errors with
file and line, ``Network.check()`` verifies name uniqueness and that ports
named in connections exist, and ``from_officespeak`` raises ``GeneratorError``
for kind-specific constraints. Each of those looks at one statement or one
agent.

This module looks at the **whole graph**: agents nothing can reach, work that
reaches no sink, sources wired to nothing, cycles with no way out. These are
the faults that produce an office which runs and does nothing, or an office
that hangs, and they are invisible to any per-statement check.

What it deliberately does not do
--------------------------------
It is static. It reads ``office.md`` and the graph it describes; it never runs
the office. In particular it **cannot** detect the deadlock class of bug --
the one where every port is wired and messages flow, but a coordinator sits
blocked on one inbox while another holds a message it will never read. Whether
that message is readable depends on how many messages each source happened to
produce and how they paired up, which is an execution history, not a property
of the graph. That is runtime hang diagnosis, and it is a different tool.

Knowing which faults are structural and which are behavioural is itself the
lesson; this module is the structural half and says so.

Codes
-----
W1  declared inbox nothing writes to -- a guaranteed block
W2  an outbox the role declares and nothing is wired to -- a
    guaranteed crash the first time the agent uses it
W3  unreachable agent -- nothing upstream can reach it
W4  dead end -- its output reaches no sink and no office output
W5  no such source or sink -- a name that is in no registry
W6  missing role file -- named a role with no ``.md`` or ``.py`` behind it
W7  cycle (note, not an error) -- legal and often intended
W8  source with no destination, or sink nothing feeds
W9  a connection naming something that is not declared anywhere
W10 a sub-office whose directory, or whose office.md, is not there
W11 (note) text from the open web can reach a sink that acts outside
    this machine -- email, chat, a webhook, an MCP tool
W12 (note) a role's own Python reaches the network, another program, or
    code built at run time -- a lint, and one that teaches rather than
    protects
W13 a connection writing to an inbox the receiving agent does not have
G1  an agent with a name and no role yet
G2  nothing leaves the office -- it has no sink

Drafts
------
An office with an agent whose job is undecided (``Jay is unassigned.``)
is a **draft**, and draft-ness is a property of the office rather than
a flag anyone passes. Its findings do not change; what they mean does.
In a finished office an unreachable agent is a fault; in one being
described a sentence at a time it is the next sentence. So the
incompleteness codes -- W1, W2, W3, W4, W8, G1, G2 -- become notes, the
report says "still to do", and the exit status is 0. There is nothing
wrong with an unfinished office, and reporting it as broken teaches a
beginner that building is a sequence of errors.

Mistakes stay errors. W5 (a component name in no registry) and W6 (a
role with no file behind it) are wrong now and will still be wrong when
the office is finished, so calling them remaining work would bury them.

G2 earns its own code because it is the only fault a person cannot
diagnose from outside. Every other mistake announces itself; an office
with no sink is structurally perfect, runs cleanly, exits zero and
produces silence.

Ports are declared, so the port checks are subtraction
------------------------------------------------------
Every role says what its inboxes and outboxes are -- a prose role in
its front matter, a Python role in the ``AgentRoleEntry`` it builds --
and ``role_ports.read_ports`` is the one function that reads them.
``dsl check``, the loader and ``dsl draw`` all call it, so they cannot
disagree about the shape of an agent.

Given the declared set on one side and what the connections wire on the
other, three of the checks here are set subtraction:

    W1   declared inbox  - wired  =  an agent that will block
    W2   declared outbox - wired  =  a send that will raise
    W13  wired inbox - declared   =  a message that reaches nothing

None of the three was possible while an agent's interface was inferred.
The ports came from a regular expression over the role's English
(``send to keep``), so there was no declaration for the wiring to
disagree with: write ``send to `keep``` and the port silently did not
exist, the office checked clean, and it produced nothing. W1 worked
only for the three coordinator kinds that spell their inboxes on the
agent line, and W2 was left unimplemented for years on the grounds that
it needed a resolved shape that nothing had.

Where a shape genuinely is unknown -- a role built by a library factory
has no file to read -- ``inports_for`` returns ``None`` and the checks
stay quiet. A check that invents a port set is worse than one that says
nothing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Set, Tuple

from dissyslab.office.office_spec import UNASSIGNED, is_draft
from dissyslab.office.role_ports import DEFAULT_INBOX, Ports
from dissyslab.office.role_effects import scan_office
from dissyslab.office.trust import (
    is_acting_sink,
    is_untrusted_source,
    what_it_does,
)

__all__ = [
    "Finding",
    "WiringReport",
    "check_office_dir",
    "check_spec",
    "declared_inports",
    "declared_outports",
    "format_report",
    "inports_for",
    "role_ports_for",
]

EXTERNAL = "external"

#: Agent-line arguments whose *value* is the name of an inbox, rather
#: than a setting. ``select(..., command="command")`` and
#: ``gate(data="data", control="control")``; ``record(initial={...})``
#: is not one, which is why this is a list and not "every string arg".
_PORT_NAMING_ARGS = {"command", "data", "control"}

# Findings that mean "not finished yet" rather than "wrong". In a draft
# office these are the remaining work; W5, W6, W9 and W13 are not,
# because a misspelled name is as wrong now as it will be later.
_INCOMPLETENESS_CODES = {"W1", "W2", "W3", "W4", "W8", "G1", "G2"}


@dataclass(frozen=True)
class Finding:
    """One thing worth telling the user about."""

    code: str
    severity: str  # "error" | "note"
    subject: str  # the agent/source/sink the finding is about
    message: str
    hint: str = ""
    #: The same finding said as remaining work rather than as a fault,
    #: for an office still being described. "Dan's 'immediate' goes
    #: nowhere yet" and "'Dan' is a dead end" are the same observation;
    #: only one of them reads as progress. Falls back to ``message``.
    gap: str = ""

    @property
    def is_error(self) -> bool:
        return self.severity == "error"


@dataclass
class WiringReport:
    office_name: str
    office_path: Path
    findings: List[Finding] = field(default_factory=list)
    skipped: List[str] = field(default_factory=list)
    #: True when the office still has an agent whose job is undecided.
    #: Its findings are then remaining work rather than faults.
    draft: bool = False

    @property
    def errors(self) -> List[Finding]:
        return [f for f in self.findings if f.is_error]

    @property
    def notes(self) -> List[Finding]:
        return [f for f in self.findings if not f.is_error]

    @property
    def ok(self) -> bool:
        return not self.errors


# --------------------------------------------------------------------------
# graph extraction
# --------------------------------------------------------------------------


@dataclass
class _Graph:
    sources: Set[str]
    sinks: Set[str]
    agents: Set[str]
    inputs: Set[str]  # office boundary inports
    outputs: Set[str]  # office boundary outports
    edges: List[Tuple[str, str]]  # (sender_name, receiver_name)
    roles: Dict[str, str]  # agent_name -> role_name

    @property
    def nodes(self) -> Set[str]:
        return self.sources | self.sinks | self.agents

    def successors(self, name: str) -> Set[str]:
        return {b for a, b in self.edges if a == name}

    def predecessors(self, name: str) -> Set[str]:
        return {a for a, b in self.edges if b == name}


def _build_graph(spec) -> _Graph:
    sources = {s.name for s in spec.sources}
    sinks = {k.name for k in spec.sinks}
    agents = {a.agent_name for a in spec.agents}
    roles = {a.agent_name: a.role_name for a in spec.agents}

    edges: List[Tuple[str, str]] = []
    for conn in spec.connections:
        sender = conn.source.name
        for dest in conn.destinations:
            edges.append((sender, dest.name))

    return _Graph(
        sources=sources,
        sinks=sinks,
        agents=agents,
        inputs=set(spec.inputs),
        outputs=set(spec.outputs),
        edges=edges,
        roles=roles,
    )


def _reachable(starts: Iterable[str], edges: Sequence[Tuple[str, str]]) -> Set[str]:
    """Forward reachability from ``starts``."""
    adj: Dict[str, Set[str]] = {}
    for a, b in edges:
        adj.setdefault(a, set()).add(b)
    seen: Set[str] = set()
    stack = list(starts)
    while stack:
        node = stack.pop()
        if node in seen:
            continue
        seen.add(node)
        stack.extend(adj.get(node, ()))
    return seen


def _looping_groups(
    nodes: Iterable[str], edges: Sequence[Tuple[str, str]]
) -> List[List[str]]:
    """Groups of agents that can loop -- strongly connected components, size > 1.

    Deliberately *not* every elementary cycle. The ``debate`` office has three
    panellists feeding one synchronizer, which produces six elementary cycles
    over what is really one loop; reporting six notes for one structure trains
    a reader to skip the notes. One component, one note.

    It also fixes a wrong answer. Three of those six cycles do not pass through
    the gate, so a per-cycle check calls them non-terminating -- on an office
    that terminates correctly. What matters is whether a gate exists *anywhere
    in the component*, since that is what can break the loop.

    Tarjan's algorithm, iterative so a deep graph cannot blow the stack.
    """
    adj: Dict[str, List[str]] = {}
    for a, b in edges:
        adj.setdefault(a, []).append(b)

    index_of: Dict[str, int] = {}
    low: Dict[str, int] = {}
    on_stack: Set[str] = set()
    stack: List[str] = []
    counter = 0
    groups: List[List[str]] = []

    for root in sorted(nodes):
        if root in index_of:
            continue
        work: List[Tuple[str, int]] = [(root, 0)]
        while work:
            node, child_i = work[-1]
            if child_i == 0:
                index_of[node] = low[node] = counter
                counter += 1
                stack.append(node)
                on_stack.add(node)

            children = adj.get(node, ())
            if child_i < len(children):
                work[-1] = (node, child_i + 1)
                child = children[child_i]
                if child not in index_of:
                    work.append((child, 0))
                elif child in on_stack:
                    low[node] = min(low[node], index_of[child])
            else:
                work.pop()
                if work:
                    parent = work[-1][0]
                    low[parent] = min(low[parent], low[node])
                if low[node] == index_of[node]:
                    component: List[str] = []
                    while True:
                        member = stack.pop()
                        on_stack.discard(member)
                        component.append(member)
                        if member == node:
                            break
                    if len(component) > 1 or node in adj.get(node, ()):
                        groups.append(sorted(component))

    return groups


# --------------------------------------------------------------------------
# role files
# --------------------------------------------------------------------------


def declared_inports(agent_spec) -> List[str]:
    """Inports an agent spells out on its own line in office.md, if any.

    ``Sync is a synchronizer(inboxes=["entities", "severity"])`` parses to
    ``args=(("inports", ["entities", "severity"]),)``. This is the
    coordinator case: a role built by a factory has no file, so the
    agent line is the only place its inboxes can be written down.

    An empty list means "not said here", not "none" -- ask
    ``inports_for`` next, which also looks at the role.
    """
    args = tuple(getattr(agent_spec, "args", ()) or ())
    ports: List[str] = []
    for key, value in args:
        if key == "inports" and isinstance(value, (list, tuple)):
            ports.extend(str(port) for port in value)
    # A coordinator can name one more inbox in an argument of its own:
    # `select(inboxes=[...], command="command")` has three inboxes, and
    # a gate's are `data` and `control`. Missing these made every
    # connection into a select's command port look like a message sent
    # to a port that does not exist.
    for key, value in args:
        if key in _PORT_NAMING_ARGS and isinstance(value, str) and value:
            if value not in ports:
                ports.append(value)
    return ports


def _resolve_role_file(office_dir: Path, role: str) -> Path | None:
    """The file the loader will actually use for this role, or None.

    Order matters and must match the loader's: a role in the office's
    own ``roles/`` wins over the library's, and ``.py`` wins over
    ``.md``. Getting this wrong makes W2 fire on `mac_speed_suite`,
    whose local ``roles/evaluator.py`` shadows the library's prose
    ``evaluator.md`` -- the Python role's ports come from its code, not
    from a sentence, and reading the wrong file invents a fault.
    """
    from dissyslab.office import library  # noqa: WPS433

    pkg_roles = Path(library.__file__).resolve().parents[1] / "roles"
    for candidate in (
        office_dir / "roles" / f"{role}.py",
        office_dir / "roles" / f"{role}.md",
        pkg_roles / f"{role}.py",
        pkg_roles / f"{role}.md",
    ):
        if candidate.is_file():
            return candidate
    return None


def role_ports_for(office_dir: Path, role: str) -> "Ports | None":
    """What a role declares, or None when nothing here can know.

    A role built by a library factory -- ``synchronizer``, ``select``,
    ``gate``, ``router`` -- has no file, and its ports come from the
    agent line. Those are handled by ``declared_inports``; this returns
    None for them rather than guessing, because a check that invents a
    port set is worse than one that stays quiet.
    """
    from dissyslab.office.role_ports import PortDeclarationError, read_ports

    path = _resolve_role_file(office_dir, role)
    if path is None:
        return None
    try:
        return read_ports(path)
    except PortDeclarationError:
        return None


def declared_outports(office_dir: Path, role: str) -> Tuple[str, ...]:
    """The outboxes a role declares. Empty when it declares none here."""
    ports = role_ports_for(office_dir, role)
    return ports.outboxes if ports else ()


def inports_for(agent_spec, office_dir: Path) -> "Tuple[str, ...] | None":
    """Every inbox this agent has, or None when nothing here can know.

    Two places an inbox set can be written down, and they do not
    overlap:

    * the **agent line**, for a role built by a factory --
      ``Sync is a synchronizer(inboxes=[...])``. There is no file to
      read, so the line is the declaration.
    * the **role file**, for everything else. Since roles declare
      their ports, this is now known for every agent with a role file
      rather than only for the three coordinator kinds.

    None means unknown, and unknown must stay silent. A sub-office
    declares its interface in its own ``office.md`` (``Inputs:``);
    reading it from here is a different job and is not done yet, so a
    sub-office returns None rather than an empty tuple -- which would
    read as "has no inboxes" and make every connection into it a
    fault.
    """
    on_the_line = declared_inports(agent_spec)
    if on_the_line:
        return tuple(on_the_line)
    if getattr(agent_spec, "path", None) is not None:
        return None
    role = getattr(agent_spec, "role_name", None)
    if not role or role == UNASSIGNED:
        return None
    ports = role_ports_for(office_dir, role)
    return ports.inboxes if ports else None


def _local_role_names(office_dir: Path) -> Set[str]:
    roles_dir = office_dir / "roles"
    if not roles_dir.is_dir():
        return set()
    names: Set[str] = set()
    for path in roles_dir.iterdir():
        if path.suffix in (".md", ".py") and not path.name.startswith("_"):
            names.add(path.stem)
    return names


def _builtin_role_names() -> Set[str]:
    """Role names resolvable without a file in the office's own ``roles/``.

    Four surfaces, and all four matter -- missing any one produces a false
    "missing role file" on an office that works:

    1. ``dissyslab/roles/`` -- the shipped English LLM-prompt roles
       (``writer``, ``entity_extractor``, ``severity_classifier``, ...).
    2. ``fn_lib.FN_LIB`` -- Python function roles (``deduplicator``).
    3. The coordinator kinds the library exposes as ``<name>_role``
       factories (``synchronizer``, ``gate``, ``select``, ``record``, ...).
    4. ``COMPONENT_REGISTRY`` / the source and sink registries, for anything
       polymorphic enough to appear in an ``Agents:`` line.

    If none of them can be read, W6 is skipped rather than guessed at: a
    false "missing role file" is worse than silence.
    """
    names: Set[str] = set()

    try:
        import dissyslab  # noqa: WPS433

        shared_roles = Path(dissyslab.__file__).parent / "roles"
        if shared_roles.is_dir():
            names |= {
                p.stem
                for p in shared_roles.iterdir()
                if p.suffix in (".md", ".py") and not p.name.startswith("_")
            }
    except Exception:  # pragma: no cover - defensive
        pass

    try:
        from dissyslab import fn_lib  # noqa: WPS433

        registry = getattr(fn_lib, "FN_LIB", None)
        if isinstance(registry, dict):
            names |= {str(k) for k in registry}
    except Exception:  # pragma: no cover - defensive
        pass

    try:
        from dissyslab.office import library, utils  # noqa: WPS433

        names |= {
            attr[: -len("_role")]
            for attr in dir(library)
            if attr.endswith("_role") and not attr.startswith("_")
        }
        for attr in ("COMPONENT_REGISTRY", "SOURCE_REGISTRY", "SINK_REGISTRY"):
            registry = getattr(utils, attr, None)
            if isinstance(registry, dict):
                names |= {str(k) for k in registry}
    except Exception:  # pragma: no cover - defensive
        pass

    return names


def _registered_component_names() -> Tuple[Set[str], Set[str]]:
    """``(source_names, sink_names)`` from the registries, or two empty sets.

    Empty means "could not read the registries", and W5 is skipped rather
    than guessed at — same rule as W6. A false "no such source" on an
    office that works would be worse than the gap it closes.
    """
    try:
        from dissyslab.office import utils  # noqa: WPS433

        sources = getattr(utils, "SOURCE_REGISTRY", None)
        sinks = getattr(utils, "SINK_REGISTRY", None)
        return (
            {str(k) for k in sources} if isinstance(sources, dict) else set(),
            {str(k) for k in sinks} if isinstance(sinks, dict) else set(),
        )
    except Exception:  # pragma: no cover - defensive
        return set(), set()


def _closest(name: str, candidates: Set[str]) -> List[str]:
    """Up to three plausible spellings of ``name``. A typo's whole value
    as a diagnostic is that the right answer is one character away."""
    import difflib

    return difflib.get_close_matches(name, sorted(candidates), n=3, cutoff=0.6)


# --------------------------------------------------------------------------
# the checks
# --------------------------------------------------------------------------


def check_spec(spec, office_dir: Path) -> WiringReport:
    """Run every structural check against an already-parsed ``OfficeSpec``."""
    graph = _build_graph(spec)
    report = WiringReport(office_name=spec.name, office_path=office_dir)

    named = graph.nodes | {EXTERNAL}

    # W1 and W13 -- the two halves of "the inboxes an agent has".
    #
    # Now that a role declares its inboxes, this set is known for every
    # agent with a role file, not only for the three coordinator kinds
    # that spelled theirs on the agent line. Both faults fall out of
    # comparing the declaration against what the connections write to:
    #
    #   W1  declared and nothing writes to it -- the agent blocks there
    #   W13 written to and not declared     -- the message goes nowhere
    #
    # W13 was silent until now, and silent in the worst way. `Screen's
    # inbx is ...` checked clean, built a connection to a port that did
    # not exist, and failed at run time with "Agent 'Screen' inport
    # 'in_' is not connected to any queue" -- naming `in_`, a port the
    # student never typed, about a line they did type.
    #
    # An unreachable agent (W3) has no inboxes wired at all, and would
    # collect a W1 for each of them on top of the W3 that explains it.
    # W3 is the finding that leads somewhere, so W1 stands down where
    # nothing at all reaches the agent.
    for agent_spec in spec.agents:
        declared_tuple = inports_for(agent_spec, office_dir)
        if declared_tuple is None:
            continue
        declared = list(declared_tuple)
        agent = agent_spec.agent_name
        written_to: Dict[str, Set[str]] = {}
        # The sending end of each wire too, so the hint can print the
        # corrected sentence rather than a sentence with a gap in it.
        senders_of: Dict[str, List[Tuple[str, str]]] = {}
        for conn in spec.connections:
            for dest in conn.destinations:
                if dest.name == agent:
                    written_to.setdefault(dest.port, set()).add(conn.source.name)
                    senders_of.setdefault(dest.port, []).append(
                        (conn.source.name, conn.source.port or "out")
                    )

        undeclared = sorted(set(written_to) - set(declared))
        for port in undeclared:
            senders = ", ".join(sorted(written_to[port]))
            near = _closest(port, set(declared))
            if near:
                fix = (
                    f"{agent}'s inboxes are: {', '.join(declared)}. "
                    f"Did you mean {' or '.join(repr(c) for c in near)}?"
                )
            elif len(declared) == 1:
                # One inbox, so the corrected line can be written out in
                # full -- and when that inbox is the default it is not
                # named at all, which is the part a beginner is least
                # likely to guess.
                only = declared[0]
                from_name, from_port = senders_of[port][0]
                tail = agent if only == DEFAULT_INBOX else f"{agent}'s {only}"
                fix = (
                    f"{agent} has one inbox, {only!r}. Write: "
                    f"{from_name}'s {from_port} is {tail}."
                )
            else:
                fix = (
                    f"{agent}'s inboxes are: {', '.join(declared)}. "
                    "Correct the spelling, or add the inbox to the role."
                )
            report.findings.append(
                Finding(
                    "W13",
                    "error",
                    agent,
                    f"{senders} writes to {agent}'s {port!r}, but {agent} has "
                    f"no inbox called {port!r} -- that message reaches nothing.",
                    fix,
                )
            )

        if not written_to:
            # Nothing reaches this agent at all. W3 says that once and
            # says why; one W1 per inbox on top of it is noise.
            continue
        if undeclared:
            # One mistake, one finding. A misspelled destination leaves
            # the real inbox unwired by construction, so every W1 here
            # is the same typo said a second way -- and fixing the
            # spelling fixes both. If the reader instead adds the port
            # they typed to the role, W1 comes back on the next run,
            # which is when it is news.
            continue
        for port in declared:
            if port in written_to:
                continue
            wired = ", ".join(
                f"{p} (from {', '.join(sorted(s))})"
                for p, s in sorted(written_to.items())
            )
            report.findings.append(
                Finding(
                    "W1",
                    "error",
                    agent,
                    f"{agent!r} declares inbox {port!r}, but nothing writes "
                    f"to it -- {agent} will block on it and never proceed.",
                    f"Declared inboxes: {', '.join(declared)}. "
                    + (f"Wired: {wired}." if wired else "None are wired.")
                    + f" Either wire something to {port!r}, or remove it from "
                    "the inboxes list.",
                    gap=f"nothing is connected to {agent}'s {port!r} inbox yet.",
                )
            )

    # W2 -- an outbox the role declares and nothing is wired to.
    #
    # The symmetric hole beside W1, and a worse one: an unwired inbox
    # blocks, which at least stops; an unwired outbox raises
    # "Outbox 'discard' of agent 'Screen' is not connected" the first
    # time the agent tries to use it. So a relevance_filter wired only
    # on `keep` passes every check and then crashes on the first
    # irrelevant article -- which, for a filter, is the point.
    #
    # This was reserved and left unimplemented because it needs the
    # role's resolved shape. It has one now: the role declares its
    # outboxes and ``read_ports`` is what the loader reads them with,
    # so the check and the office cannot disagree.
    #
    # Silent on all forty-one shipped offices.
    for agent_spec in spec.agents:
        role = getattr(agent_spec, "role_name", None)
        if not role or role == UNASSIGNED or agent_spec.path is not None:
            continue
        declared_out = declared_outports(office_dir, role)
        if not declared_out:
            continue
        agent = agent_spec.agent_name
        wired_out = {
            conn.source.port for conn in spec.connections
            if conn.source.name == agent
        }
        for port in declared_out:
            if port in wired_out:
                continue
            report.findings.append(
                Finding(
                    "W2",
                    "error",
                    agent,
                    f"{agent!r} sends to {port!r}, but {port!r} is connected "
                    f"to nothing -- the run stops the first time it is used.",
                    f"The role {role!r} declares {port!r} as an outbox. "
                    f"Either wire it -- {agent}'s {port} is <somewhere>. -- "
                    f"or take {port!r} out of the role's outboxes.",
                    gap=f"{agent}'s {port!r} goes nowhere yet.",
                )
            )

    # W8 -- sources and sinks that are not actually plugged in.
    for source in sorted(graph.sources):
        if not graph.successors(source):
            report.findings.append(
                Finding(
                    "W8",
                    "error",
                    source,
                    f"source {source!r} has no destination -- nothing reads what it fetches.",
                    "Add a line such as: "
                    f"{source}'s destination is <agent>.",
                    gap=f"nothing reads {source} yet.",
                )
            )
    for sink in sorted(graph.sinks):
        if not graph.predecessors(sink):
            report.findings.append(
                Finding(
                    "W8",
                    "error",
                    sink,
                    f"sink {sink!r} is never sent anything -- it will produce no output.",
                    f"Add a line such as: <agent>'s out is {sink}.",
                    gap=f"nothing is sent to {sink} yet.",
                )
            )

    # W3 -- agents nothing upstream can reach.
    entry_points = graph.sources | ({EXTERNAL} if graph.inputs else set())
    reachable = _reachable(entry_points, graph.edges)
    for agent in sorted(graph.agents):
        if agent not in reachable:
            feeders = graph.predecessors(agent)
            hint = (
                "Nothing connects to it at all."
                if not feeders
                else "It is fed only by "
                + ", ".join(sorted(feeders))
                + ", which nothing upstream reaches either."
            )
            report.findings.append(
                Finding(
                    "W3",
                    "error",
                    agent,
                    f"{agent!r} is unreachable -- no path from any source.",
                    hint,
                    gap=f"nothing reaches {agent} yet.",
                )
            )

    # W4 -- work that reaches no sink and no office output.
    #
    # Report the *frontier*, not every affected agent. Deleting one wire
    # into the sinks of a seven-agent office makes all seven dead ends,
    # and reporting seven faults for one missing wire is, for a
    # first-year, worse than reporting none: it reads as seven separate
    # things to fix and buries the one place to look.
    #
    # Every successor of a dead agent is itself dead -- if any successor
    # reached an exit, so would the agent. So the frontier is exactly
    # the dead agents with no dead successor, which is where the path to
    # a sink actually stops. The rest are consequences, and are counted
    # rather than listed.
    exits = graph.sinks | ({EXTERNAL} if graph.outputs else set())
    reverse_edges = [(b, a) for a, b in graph.edges]
    reaches_exit = _reachable(exits, reverse_edges)
    dead = {
        a for a in graph.agents
        if a in reachable and a not in reaches_exit
    }
    dead_successors: Dict[str, Set[str]] = {a: set() for a in dead}
    for src, dst in graph.edges:
        if src in dead and dst in dead:
            dead_successors[src].add(dst)

    frontier = {a for a in dead if not dead_successors[a]}
    # A dead cycle has no frontier -- every member has a dead successor.
    # Report the whole cycle rather than nothing.
    if dead and not frontier:
        frontier = dead

    for agent in sorted(frontier):
        upstream = sorted(dead - frontier)
        hint = (
            "Whatever it computes is discarded. Wire its out to a sink "
            "or to an agent that leads to one."
        )
        if upstream:
            shown = ", ".join(upstream[:5])
            more = f", and {len(upstream) - 5} more" if len(upstream) > 5 else ""
            hint += (
                f"\n      {len(upstream)} agent(s) upstream are dead ends "
                f"only because of this one ({shown}{more}); fixing this "
                f"should clear them."
            )
        report.findings.append(
            Finding(
                "W4",
                "error",
                agent,
                f"{agent!r} is a dead end -- its output reaches no sink.",
                hint,
                gap=f"{agent}'s output goes nowhere yet.",
            )
        )

    # W5 -- a source or sink name that is in no registry.
    #
    # Found by the E5 acceptance trial, 2026-08-17, and it is the worst
    # gap the checker had. `Sources: bbc_wolrd` passed `dsl check` clean,
    # passed `dsl build` clean, and then died at run time with
    # `NameError: name 'bbc_wolrd' is not defined` pointing into
    # generated code the student never wrote. Check clean, build clean,
    # traceback: the exact sequence the checker exists to prevent.
    #
    # W6 covers *role* names only, and the skill's promise that the check
    # catches unknown names read as though it covered these too.
    reg_sources, reg_sinks = _registered_component_names()
    for kind, declared, registered in (
        ("source", graph.sources, reg_sources),
        ("sink", graph.sinks, reg_sinks),
    ):
        if not registered:
            continue  # registries unreadable; say nothing
        for name in sorted(declared):
            if name in registered:
                continue
            suggestions = _closest(name, registered)
            hint = (
                f"Did you mean {' or '.join(repr(s) for s in suggestions)}?"
                if suggestions
                else f"No {kind} by that name is registered."
            )
            report.findings.append(
                Finding(
                    "W5",
                    "error",
                    name,
                    f"there is no {kind} called {name!r}.",
                    hint + f"  Run `dsl list` to see every shipped {kind}, "
                    f"or see docs/SOURCES_AND_SINKS.md.",
                )
            )

    # W6 -- named a role with nothing behind it.
    builtins = _builtin_role_names()
    if builtins:
        local = _local_role_names(office_dir)
        sub_offices = {a.agent_name for a in spec.agents if a.path is not None}
        for agent in sorted(graph.agents):
            role = graph.roles.get(agent, "")
            if role == UNASSIGNED:
                # Not a missing file. G1 reports it as a missing decision,
                # which is what it is and what the user can act on.
                continue
            if agent in sub_offices:
                # Its "role name" is the last segment of a directory
                # path. W10 checks the directory; asking whether there
                # is a roles/news.md for `X is an office at ../news.`
                # is a question about the wrong thing.
                continue
            if role and role not in local and role not in builtins:
                report.findings.append(
                    Finding(
                        "W6",
                        "error",
                        agent,
                        f"{agent!r} is a {role!r}, but there is no "
                        f"roles/{role}.md or roles/{role}.py, and {role!r} is "
                        "not a built-in role.",
                        "Create the role file, or correct the spelling.",
                    )
                )
    else:  # pragma: no cover - defensive
        report.skipped.append("W6 (could not determine the built-in role names)")

    # W7 -- feedback loops. Legal, frequently intended, always worth naming.
    for group in _looping_groups(graph.agents, graph.edges):
        gates = [n for n in group if "gate" in graph.roles.get(n, "")]
        members = ", ".join(group)
        if gates:
            message = (
                f"{members} form a feedback loop, gated by "
                f"{' and '.join(gates)} -- so it can terminate."
            )
            hint = ""
        else:
            message = f"{members} form a feedback loop with no gate."
            hint = (
                "Loops are legal and often intended, but nothing in this one "
                "decides when to stop. Confirm that is what you meant."
            )
        report.findings.append(Finding("W7", "note", group[0], message, hint))

    # Names used in connections that are nothing at all. The compiler catches
    # this too, but catching it here means one report instead of two runs.
    for conn in spec.connections:
        for endpoint in (conn.source, *conn.destinations):
            if endpoint.name not in named:
                report.findings.append(
                    Finding(
                        "W9",
                        "error",
                        endpoint.name,
                        f"connection references {endpoint.name!r}, which is not "
                        "a declared source, sink, or agent.",
                        "Check the spelling against the Agents section.",
                    )
                )

    # W10 -- a sub-office whose directory is not there.
    #
    # Nothing checked this until now, because check_wiring read only
    # ``role_name`` and never ``path``. So `X is an office at ./nowhere.`
    # came out as W6, "there is no roles/nowhere.md" -- a clear sentence
    # about a file the office was never looking for. The real answer is
    # at compile time, several steps later, and mentions a directory the
    # reader has by then stopped thinking about.
    for agent_spec in spec.agents:
        if agent_spec.path is None:
            continue
        target = (office_dir / agent_spec.path).resolve()
        if (target / "office.md").is_file():
            continue
        if target.is_dir():
            detail = f"{target} exists but has no office.md in it."
        else:
            detail = f"There is no directory at {target}."
        report.findings.append(
            Finding(
                "W10",
                "error",
                agent_spec.agent_name,
                f"{agent_spec.agent_name!r} is an office at "
                f"{agent_spec.path!r}, but that office is not there.",
                detail + " The path is relative to this office's folder.",
            )
        )

    # G1 -- an agent with a name and no role yet.
    for agent_spec in spec.agents:
        if agent_spec.role_name == UNASSIGNED and agent_spec.path is None:
            report.findings.append(
                Finding(
                    "G1",
                    "error",
                    agent_spec.agent_name,
                    f"{agent_spec.agent_name!r} has no role yet.",
                    "Say what it does and it will be written down.",
                )
            )

    # G2 -- nothing leaves the office.
    #
    # This one has a line of its own because it is the only fault a
    # person cannot diagnose from the outside. Every other mistake
    # announces itself: the office refuses to build, or hangs, or names
    # the thing it could not find. An office with no sink is
    # structurally perfect, runs cleanly, exits zero and produces
    # silence, and the reasonable conclusion from that is that the
    # framework is broken.
    #
    # An open office is exempt: its Outputs are how work leaves it, and
    # the office that embeds it owns the sink.
    if not spec.sinks and not spec.outputs:
        report.findings.append(
            Finding(
                "G2",
                "error",
                spec.name,
                "nothing leaves this office -- it has no sink.",
                "It will run, finish and show you nothing. Add a sink:"
                "\n            console_printer to see the output, or"
                "\n            jsonl_recorder(path=\"...\") to keep it.",
            )
        )

    # W11 -- text from the open web can reach something that acts.
    #
    # The first check here that is about consequences rather than
    # structure. An agent's job can be a paragraph of English run by a
    # language model; when the message it reads was fetched from the
    # open web, the words in it were chosen by a stranger. Nothing in
    # the role file prevents a stranger from writing instructions, so
    # what is worth bounding is not the agent but the damage: an office
    # affects the world only through its sinks.
    #
    # So the question is reachability, on the graph already built for
    # W3 and W4 -- can an untrusted source reach an acting sink. See
    # trust.py for what puts a component in each class.
    #
    # A note, not an error, and deliberately. There is no gate concept
    # yet, so this cannot tell a guarded path from an unguarded one,
    # and an error on an office somebody built on purpose would teach
    # them to stop reading the section it prints in. It says what the
    # office can do and leaves the judgment where the judgment is.
    # Sinks fed by the same sources are grouped into one finding, for
    # the reason W4 reports a frontier: job_hunter has four Gmail sinks
    # behind one set of job boards, and four notes about one shape
    # reads as four things to think about.
    acting_sinks = sorted(k.name for k in spec.sinks if is_acting_sink(k.name))
    untrusted = sorted(s.name for s in spec.sources if is_untrusted_source(s.name))
    if acting_sinks and untrusted:
        reverse_edges = [(b, a) for a, b in graph.edges]
        grouped: Dict[Tuple[str, ...], List[str]] = {}
        for sink_name in acting_sinks:
            feeders = _reachable([sink_name], reverse_edges)
            upstream = tuple(s for s in untrusted if s in feeders)
            if upstream:
                grouped.setdefault(upstream, []).append(sink_name)

        for upstream, sinks in sorted(grouped.items()):
            does = sorted({what_it_does(s) for s in sinks})
            report.findings.append(
                Finding(
                    "W11",
                    "note",
                    sinks[0] if len(sinks) == 1 else spec.name,
                    f"text from {', '.join(upstream)} can reach "
                    f"{', '.join(sinks)} -- which "
                    f"{' and '.join(does)}.",
                    "Whoever writes what those sources carry is writing "
                    "to an agent\n"
                    "            whose job is English run by a model, "
                    "and through it to this sink.\n"
                    "            If that is what you meant, nothing to "
                    "do. If not, send on only\n"
                    "            fields you chose -- a score, a label, "
                    "a URL -- rather than\n"
                    "            whatever the model wrote.",
                )
            )

    # W12 -- what a role's own Python reaches for.
    #
    # A lint, and deliberately a teaching one. The exposure it points
    # at is not this project's: any student running any
    # assistant-written Python has it, and a sandbox to solve one
    # instance of a general problem would be overreach.
    #
    # What *is* this project's is the claim. A plain script promises
    # nothing; an office says its power is its Sources and Sinks. That
    # sentence is true of the office and not of the Python inside a
    # role, so this exists to keep it honest -- and to put the general
    # lesson in front of someone at the one moment it is concrete,
    # which is when they have just been handed code they did not write.
    #
    # It reads imports. It cannot see what the code does.
    # Grouped by file, for the reason W4 reports a frontier: one file
    # that imports subprocess and calls subprocess.run is one thing to
    # look at, not two.
    by_file: Dict[Path, List[str]] = {}
    for effect in scan_office(office_dir):
        by_file.setdefault(effect.path, []).append(effect.detail)

    for path, details in sorted(by_file.items()):
        report.findings.append(
            Finding(
                "W12",
                "note",
                path.name,
                f"{path.parent.name}/{path.name} "
                + "; ".join(details) + ".",
                "An office's declared power is its Sources and Sinks."
                "\n            Python inside a role can act outside "
                "that, and this check"
                "\n            only reads imports -- it cannot see what "
                "the code does."
                "\n            If you did not write this file, read it.",
            )
        )

    # Draft framing.
    #
    # An office with an agent whose job is undecided is a draft. Its
    # findings do not change; what they mean does. In a finished office
    # an unreachable agent is a fault; in one being described a
    # sentence at a time it is the next sentence. So the incompleteness
    # codes become notes and `dsl check` exits 0 -- there is nothing
    # wrong with an unfinished office, and reporting it as broken
    # teaches a beginner that building is a sequence of errors.
    #
    # Mistakes stay errors. A source name that is in no registry (W5)
    # or a role with no file behind it (W6) is wrong now and will still
    # be wrong when the office is finished; calling it "remaining work"
    # would bury it.
    if is_draft(spec):
        report.draft = True
        report.findings = [
            Finding(f.code, "note", f.subject, f.gap or f.message, f.hint, f.gap)
            if f.code in _INCOMPLETENESS_CODES else f
            for f in report.findings
        ]

    return report


def check_office_dir(office_dir: Path) -> WiringReport:
    """Parse ``office_dir`` and check it."""
    from dissyslab.office.parser import parse_office_dir

    office_dir = Path(office_dir)
    spec = parse_office_dir(office_dir)
    return check_spec(spec, office_dir)


# --------------------------------------------------------------------------
# reporting
# --------------------------------------------------------------------------


def _hint_lines(hint: str, indent: int) -> List[str]:
    """A hint, indented to match the report it is being printed in.

    Hints that need more than one line used to carry their own leading
    spaces in the string literal. That worked in the ordinary report and
    misaligned in a draft's, which indents four columns further -- the
    author of the hint cannot know which report it will appear in. So
    the writer supplies the line breaks and the printer supplies the
    indentation.
    """
    pad = " " * indent
    return [pad + line.strip() for line in hint.split("\n")]


def format_report(report: WiringReport) -> str:
    """Plain text, every finding, grouped -- no traceback, no first-error-only."""
    errors, notes = report.errors, report.notes

    # A draft is not a broken office, and its report should not read
    # like a list of failures. Same findings, same order, different
    # word -- and that word is most of what makes an unfinished office
    # feel like progress rather than a pile of mistakes.
    if report.draft and not errors:
        lines = [
            f"check_wiring: {report.office_path}/office.md -- draft, "
            f"{len(notes)} thing{'s' if len(notes) != 1 else ''} still to do",
            "",
        ]
        for finding in notes:
            lines.append(f"  {'still to do':<14}{finding.message}")
            if finding.hint:
                lines.extend(_hint_lines(finding.hint, 16))
            lines.append("")
        for skipped in report.skipped:
            lines.append(f"  skipped: {skipped}")
        return "\n".join(lines).rstrip() + "\n"

    header_bits = []
    if errors:
        header_bits.append(f"{len(errors)} problem{'s' if len(errors) != 1 else ''}")
    if notes:
        header_bits.append(f"{len(notes)} note{'s' if len(notes) != 1 else ''}")
    summary = ", ".join(header_bits) if header_bits else "no problems"
    if report.draft:
        summary = "draft, " + summary

    lines = [f"check_wiring: {report.office_path}/office.md -- {summary}"]
    if not errors and not notes:
        return lines[0] + "\n"

    lines.append("")
    for finding in errors + notes:
        # The severity leads, not the code. `W13` is meaningless to
        # someone meeting it for the first time, and it was the first
        # thing on the line -- so every finding opened with a token
        # that carried nothing and pushed the sentence that did carry
        # something to the right. The draft branch above already reads
        # `still to do`; this is the same choice for the other case.
        #
        # The code stays, at the end, next to the command that explains
        # it. It is worth keeping: it survives rewording, it lets a
        # test say which check it pins, and it lets two people refer to
        # the same finding without quoting a sentence at each other.
        # None of those readers is the student meeting it once.
        label = "problem" if finding.is_error else "note"
        lines.append(f"  {label:<10}{finding.message}")
        if finding.hint:
            lines.extend(_hint_lines(finding.hint, 12))
        lines.append(f"{' ' * 12}what this means: dsl checks {finding.code}")
        lines.append("")
    for skipped in report.skipped:
        lines.append(f"  skipped: {skipped}")

    while lines and not lines[-1]:
        lines.pop()
    return "\n".join(lines).rstrip() + "\n"


def main(argv: Sequence[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        prog="check_wiring",
        description="Static wiring checks for an office directory.",
    )
    parser.add_argument("office_dir", nargs="?", default=".", type=Path)
    args = parser.parse_args(argv)

    report = check_office_dir(args.office_dir)
    print(format_report(report), end="")
    return 0 if report.ok else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
