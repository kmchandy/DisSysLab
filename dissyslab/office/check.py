"""``dsl check`` for an office in the new syntax: every problem, nothing run.

``check_office(folder)`` reports, with line numbers, everything that
would stop ``dsl run`` from building the office, without building it:

1. the syntax of ``office.md`` (the first syntax error stops the check,
   because the lines after it cannot be trusted);
2. every kind that refers to nothing (:mod:`dissyslab.office.resolve`);
3. the front matter of every role and local component, and the packages
   its ``needs:`` lists that are not installed;
4. the arguments of English roles, routers, synchronizers and gates;
5. every nested office, checked the same way;
6. every arrow whose port does not exist.

It never constructs a role, source or sink: constructing one can load a
model or open a connection (paper port 8, finding 1). The checks in
steps 4 and 6 are the ones ``build`` itself makes, called here, so the
two cannot disagree.

An ``unassigned`` agent makes the office a draft (spec 3.5): it is
reported as a note, not a problem, because an unfinished office is not a
broken one.

Not here yet: the whole-network checks (an agent nothing reaches, work
that reaches no sink, a sink nothing feeds), spec section 9, W16-W32.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from dissyslab.agents.python_role import missing_packages
from dissyslab.office.build import (
    BuildError,
    _gate,
    _Ports,
    _router,
    _runtime_connection,
    _synchronizer,
    english_args_problem,
)
from dissyslab.office.frontmatter import FrontMatterError, read_front_matter
from dissyslab.office.model import Declaration, OfficeFile
from dissyslab.office.resolve import Found, resolve_office
from dissyslab.office.syntax import OfficeSyntaxError, parse_office_file


@dataclass
class Report:
    """What ``check_office`` found. ``ok`` when there are no problems."""

    problems: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.problems


def _file_problems(decl: Declaration, found: Found, office_dir: Path) -> list[str]:
    """Front matter and ``needs:`` of a role or local component's file."""
    assert found.path is not None
    where = found.path.relative_to(office_dir) if found.path.is_relative_to(office_dir) \
        else found.path.name
    try:
        fm = read_front_matter(found.path)
    except FrontMatterError as exc:
        return [f"line {decl.line}: {where}: {exc}"]
    problems: list[str] = []
    missing = missing_packages(fm)
    if missing:
        problems.append(
            f"line {decl.line}: {where} needs {', '.join(missing)}, not installed. "
            f"Run: pip install {' '.join(missing)}"
        )
    if found.language == "english":
        problem = english_args_problem(decl)
        if problem:
            problems.append(problem)
    return problems


def _reserved_problem(decl: Declaration, found: Found, office: OfficeFile) -> str | None:
    """Build a router, synchronizer or gate (cheap, nothing outside) to check its args."""
    build = {"router": lambda: _router(decl, office),
             "synchronizer": lambda: _synchronizer(decl, office),
             "gate": lambda: _gate(decl)}.get(found.kind)
    if build is None:
        return None
    try:
        build()
    except BuildError as exc:
        return str(exc)
    return None


def _nested(
    decl: Declaration, office_dir: Path, stack: tuple[Path, ...], report: Report
) -> tuple[tuple[str, ...], tuple[str, ...]] | None:
    """Check a nested office; return its (inputs, outputs), or None if unusable."""
    args = dict(decl.args)
    rel = args.pop("path", None)
    if not isinstance(rel, str) or args:
        report.problems.append(
            f"line {decl.line}: a nested office is {decl.name}: office(path=\"<folder>\")."
        )
        return None
    sub_dir = (office_dir / rel).resolve()
    if not (sub_dir / "office.md").is_file():
        report.problems.append(f"line {decl.line}: there is no office.md in {sub_dir}.")
        return None
    if sub_dir in stack:
        report.problems.append(f"line {decl.line}: {sub_dir.name} contains itself.")
        return None
    sub_report, sub = _check(sub_dir, stack + (sub_dir,))
    prefix = f"in {rel.rstrip('/')}/office.md, "
    report.problems.extend(prefix + p for p in sub_report.problems)
    report.notes.extend(prefix + n for n in sub_report.notes)
    if sub is None:
        return None
    if not sub.inputs and not sub.outputs:
        report.problems.append(
            f"line {decl.line}: {sub_dir.name} has no inputs: or outputs:, so it "
            "cannot be part of another office."
        )
        return None
    return sub.inputs, sub.outputs


def _check(office_dir: Path, stack: tuple[Path, ...]) -> tuple[Report, OfficeFile | None]:
    report = Report()
    try:
        office = parse_office_file(office_dir / "office.md")
    except OfficeSyntaxError as exc:
        report.problems.append(str(exc))
        return report, None

    found, unresolved = resolve_office(office, office_dir)
    report.problems.extend(f"line {p.line}: {p.message}" for p in unresolved)

    ports = _Ports(found=found, inputs=office.inputs, outputs=office.outputs)
    for decl in office.declarations:
        f = found.get(decl.name)
        if f is None:
            continue
        if f.path is not None:
            report.problems.extend(_file_problems(decl, f, office_dir))
        elif f.kind == "unassigned":
            report.notes.append(
                f"line {decl.line}: {decl.name} is unassigned, so this office is a draft: "
                "it can be checked, not run."
            )
        elif f.kind == "office":
            sub_ports = _nested(decl, office_dir, stack, report)
            if sub_ports is not None:
                ports.nested[decl.name] = sub_ports
        else:
            problem = _reserved_problem(decl, f, office)
            if problem:
                report.problems.append(problem)

    for c in office.connections:
        ends = (c.sender.name, c.receiver.name)
        if any(n not in found and n not in office.inputs + office.outputs for n in ends):
            continue  # already reported as a kind that refers to nothing
        if any(found.get(n) is not None and found[n].kind == "office"
               and n not in ports.nested for n in ends):
            continue  # the nested office itself is already reported
        try:
            _runtime_connection(c, ports)
        except BuildError as exc:
            report.problems.append(str(exc))
    return report, office


def check_office(office_dir: Path) -> Report:
    """Every problem in the office at ``office_dir``, without building it."""
    office_dir = office_dir.resolve()
    report, _ = _check(office_dir, (office_dir,))
    report.problems.sort(key=_line_number)
    report.notes.sort(key=_line_number)
    return report


def _line_number(text: str) -> int:
    """The N of a leading ``line N:``; problems inside a nested office sort last."""
    head = text.split(":", 1)[0]
    return int(head[5:]) if head.startswith("line ") and head[5:].isdigit() else 10**9


def format_report(name: str, report: Report) -> str:
    """The report as ``dsl check`` prints it."""
    lines = [f"{name}/office.md:"]
    lines += [f"  problem: {p}" for p in report.problems]
    lines += [f"  note: {n}" for n in report.notes]
    if report.ok:
        lines.append("  no problems found." if not report.notes else "  no other problems.")
    return "\n".join(lines) + "\n"
