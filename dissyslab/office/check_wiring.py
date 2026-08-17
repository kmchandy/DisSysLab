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
of the org chart. That is runtime hang diagnosis, and it is a different tool.

Knowing which faults are structural and which are behavioural is itself the
lesson; this module is the structural half and says so.

Codes
-----
W3  unreachable agent -- nothing upstream can reach it
W4  dead end -- its output reaches no sink and no office output
W6  missing role file -- named a role with no ``.md`` or ``.py`` behind it
W7  cycle (note, not an error) -- legal and often intended
W8  source with no destination, or sink nothing feeds

W1 (an inport nothing writes to) and W2 (an outport nothing reads) need each
role's declared port shape, which the parser does not resolve -- for most
office.md agents the ports are *inferred from the connections themselves*, so
an unwired port cannot arise. They are meaningful only for roles with an
intrinsic shape (a Python role declaring its ports, or a built-in kind such as
``gate`` that requires specific ones). Left for a later pass rather than
implemented half-way.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Set, Tuple

__all__ = ["Finding", "WiringReport", "check_office_dir", "check_spec", "format_report"]

EXTERNAL = "external"


@dataclass(frozen=True)
class Finding:
    """One thing worth telling the user about."""

    code: str
    severity: str  # "error" | "note"
    subject: str  # the agent/source/sink the finding is about
    message: str
    hint: str = ""

    @property
    def is_error(self) -> bool:
        return self.severity == "error"


@dataclass
class WiringReport:
    office_name: str
    office_path: Path
    findings: List[Finding] = field(default_factory=list)
    skipped: List[str] = field(default_factory=list)

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


def _find_cycles(nodes: Iterable[str], edges: Sequence[Tuple[str, str]]) -> List[List[str]]:
    """Every elementary cycle, as node lists. Small graphs -- plain DFS is fine."""
    adj: Dict[str, List[str]] = {}
    for a, b in edges:
        adj.setdefault(a, []).append(b)

    cycles: List[List[str]] = []
    seen_signatures: Set[frozenset] = set()

    def walk(start: str, node: str, path: List[str], on_path: Set[str]) -> None:
        for nxt in adj.get(node, ()):
            if nxt == start:
                signature = frozenset(path)
                if signature not in seen_signatures:
                    seen_signatures.add(signature)
                    cycles.append(list(path))
            elif nxt not in on_path:
                path.append(nxt)
                on_path.add(nxt)
                walk(start, nxt, path, on_path)
                path.pop()
                on_path.discard(nxt)

    for start in sorted(nodes):
        walk(start, start, [start], {start})
    return cycles


# --------------------------------------------------------------------------
# role files
# --------------------------------------------------------------------------


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


# --------------------------------------------------------------------------
# the checks
# --------------------------------------------------------------------------


def check_spec(spec, office_dir: Path) -> WiringReport:
    """Run every structural check against an already-parsed ``OfficeSpec``."""
    graph = _build_graph(spec)
    report = WiringReport(office_name=spec.name, office_path=office_dir)

    named = graph.nodes | {EXTERNAL}

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
                )
            )

    # W4 -- work that reaches no sink and no office output.
    exits = graph.sinks | ({EXTERNAL} if graph.outputs else set())
    reverse_edges = [(b, a) for a, b in graph.edges]
    reaches_exit = _reachable(exits, reverse_edges)
    for agent in sorted(graph.agents):
        if agent in reachable and agent not in reaches_exit:
            report.findings.append(
                Finding(
                    "W4",
                    "error",
                    agent,
                    f"{agent!r} is a dead end -- its output reaches no sink.",
                    "Whatever it computes is discarded. Wire its out to a sink "
                    "or to an agent that leads to one.",
                )
            )

    # W6 -- named a role with nothing behind it.
    builtins = _builtin_role_names()
    if builtins:
        local = _local_role_names(office_dir)
        for agent in sorted(graph.agents):
            role = graph.roles.get(agent, "")
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

    # W7 -- cycles. Legal, frequently intended, always worth naming.
    for cycle in _find_cycles(graph.agents, graph.edges):
        has_gate = any(graph.roles.get(n, "").endswith("gate") for n in cycle)
        path = " -> ".join(cycle + [cycle[0]])
        if has_gate:
            message = f"cycle {path} (has a gate, so it can terminate)."
            hint = ""
        else:
            message = f"cycle {path}."
            hint = (
                "Cycles are legal, but this one has no gate, so nothing in it "
                "decides when to stop. Confirm that is what you meant."
            )
        report.findings.append(Finding("W7", "note", cycle[0], message, hint))

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


def format_report(report: WiringReport) -> str:
    """Plain text, every finding, grouped -- no traceback, no first-error-only."""
    errors, notes = report.errors, report.notes
    header_bits = []
    if errors:
        header_bits.append(f"{len(errors)} problem{'s' if len(errors) != 1 else ''}")
    if notes:
        header_bits.append(f"{len(notes)} note{'s' if len(notes) != 1 else ''}")
    summary = ", ".join(header_bits) if header_bits else "no problems"

    lines = [f"check_wiring: {report.office_path}/office.md -- {summary}"]
    if not errors and not notes:
        return lines[0]

    lines.append("")
    for finding in errors + notes:
        label = finding.code if finding.is_error else f"{finding.code}  note:"
        lines.append(f"  {label:<10}{finding.message}")
        if finding.hint:
            lines.append(f"{'':<12}{finding.hint}")
        lines.append("")
    for skipped in report.skipped:
        lines.append(f"  skipped: {skipped}")
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
