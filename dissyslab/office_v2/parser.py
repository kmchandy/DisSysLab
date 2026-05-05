"""
Hand-written parser for office.md.

A small, deterministic, line-numbered parser. The grammar of an
office description is small and regular enough that a hand-written
parser is both shorter and stricter than an LLM-driven equivalent
(the v1 approach this module replaces), and never flakes.

Public entry point
==================

``parse_office_dir(dir_path) -> OfficeSpec``
    Reads ``office.md`` from ``dir_path`` and returns an
    ``OfficeSpec``. Raises ``ParseError`` (with file, line number,
    and a snippet of the offending line) on bad input.

This parser reads **only** the office's own ``office.md`` — it does
not open ``roles/*.md`` or any sub-office's ``office.md``. Role
discovery (and port-shape extraction) is the role library's job
(see ``office_v2.library.load_roles_dir``); sub-office recursion is
the compiler's job (Layer 5). Each ``Agents:`` line — leaf or
sub-office — produces a uniform ``RoleRef``; for the inline form
``X is an office at <path>.`` the parser captures the path so
Layer 5 can auto-register an ``OfficeRoleEntry``, but the parser
itself never reads that path.

Grammar (informally)
====================

::

    office.md
    # Office: <name>

    [Inputs:  <name>, <name>, ...]
    [Outputs: <name>, <name>, ...]
    [Sources: <decl>, <decl>, ...]
    [Sinks:   <decl>, <decl>, ...]

    Agents:
    <agent_name> is a[n] <role_name>.
    <agent_name> is an office at <path>.

    Connections:
    <sender>'s <port> is <recipient>.
    <sender>'s <port> are <recipient>, <recipient>, ... and <recipient>.

* ``<decl>`` is a name with optional kw-args:
  ``hacker_news`` or ``hacker_news(max_articles=10)``.
* ``<recipient>`` is a bare name (agent / sink / declared output)
  or ``<sub_office>'s <port>`` for cross-office wiring.
* Sections may appear in any order. Section headers are
  case-insensitive (``Sources:`` == ``sources:``).
* Trailing periods on Agent and Connection lines are optional.
* Multi-line continuations are recognised in ``Sources:`` and
  ``Sinks:`` only — a trailing comma signals "more on the next
  line".

Boundary normalisation
======================

When the user writes ``article_in's destination is Alex.`` in an
open office that declares ``article_in`` in ``Inputs:``, the
sender refers to the office boundary. The parser rewrites the
statement so its source becomes ``Endpoint("external",
"article_in")``. Symmetrically, when a destination's name
matches one of the declared ``Outputs:``, the parser rewrites it
to ``Endpoint("external", <output_name>)``. After this pass,
boundary-touching connections are uniformly represented and the
compiler does not need to special-case them.

Tolerance / forgiveness
=======================

The parser tries to be permissive about whitespace and punctuation
the user is likely to vary:

* Whitespace is collapsed inside lists.
* Trailing ``"."`` is stripped from agent and connection lines.
* Section headers are case-insensitive.
* "and" vs ", " in plurals is accepted in any combination.

It is NOT permissive about:

* Unknown sections — surfaced rather than ignored.
* Missing required fields — surfaced.
* Ambiguous syntax — surfaced.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from dissyslab.office_v2._parser_text import (
    _Line,
    _Section,
    _enumerate_lines,
    _join_continuations,
    _parse_decl,
    _parse_doc_header,
    _parse_kw_args,
    _split_sections,
    _split_top_level,
    _strip_bullet,
    _strip_trailing_period,
)
from dissyslab.office_v2.office_spec_constants import EXTERNAL
from dissyslab.office_v2.office_spec import (
    ConnectionStmt,
    Endpoint,
    OfficeSpec,
    RoleRef,
    SinkSpec,
    SourceSpec,
)
from dissyslab.office_v2.parser_errors import ParseError


# The implicit single inport name. Matches the runtime convention in
# dissyslab/core.py:298-306 (default_inport = "in_"). Choosing the
# same name here saves one translation step at the Layer-4 → Layer-5
# boundary.
IMPLICIT_INPORT: str = "in_"


# ── Inputs / Outputs ───────────────────────────────────────────────────


def _parse_name_list(
    body: List[_Line], path: Optional[Path], section: str
) -> Tuple[Tuple[str, ...], int]:
    """Parse a comma-separated list of plain names from a section body.

    Returns the list of names and the line number to attribute errors
    to (the first line of the section, for error messages).
    """
    if not body:
        return (), 0
    text = " ".join(line.text.strip() for line in body)
    line_no = body[0].no
    snippet = body[0].text
    pieces = _split_top_level(text, ",")
    names: List[str] = []
    for p in pieces:
        if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", p):
            raise ParseError(
                f"{section}: expected a simple name, got {p!r}",
                path=path,
                line_no=line_no,
                snippet=snippet,
            )
        names.append(p)
    return tuple(names), line_no


# ── Sources / Sinks ────────────────────────────────────────────────────


def _parse_decl_section(
    body: List[_Line],
    path: Optional[Path],
    section: str,
) -> List[Tuple[str, Tuple[Tuple[str, Any], ...], int, str]]:
    """Parse the ``Sources:`` / ``Sinks:`` body.

    Returns a list of ``(name, args, line_no, snippet)`` tuples;
    callers wrap ``name`` and ``args`` in SourceSpec / SinkSpec.
    """
    folded = _join_continuations(body)
    out: List[Tuple[str, Tuple[Tuple[str, Any], ...], int, str]] = []
    for line in folded:
        text = _strip_bullet(line.text)
        for piece in _split_top_level(text, ","):
            name, args = _parse_decl(piece, path, line.no, line.text)
            out.append((name, args, line.no, line.text))
    if not out:
        # An empty section is allowed (e.g., an open office may have
        # no sources of its own).
        return []
    return out


# ── Agents ─────────────────────────────────────────────────────────────


_AGENT_LINE_RE = re.compile(
    r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s+(?:is|are)\s+an?\s+(.+?)\s*$"
)


def _parse_agents_section(
    body: List[_Line], path: Optional[Path]
) -> Tuple[List[Tuple[str, str, _Line]], List[Tuple[str, str, _Line]]]:
    """Split agent lines into (leaf_agents, sub_offices).

    leaf_agents:  list of (agent_name, role_name, line)
    sub_offices:  list of (agent_name, path_str,  line)

    Two sentence forms are recognised:

    * ``Susan is an editor.``  (leaf agent)
    * ``X is an office at <path>.`` (sub-office)
    * ``X is <name>``  (legacy network.md ``Offices:`` form, where
      <name> is itself a path; treated as a sub-office)
    """
    leaves: List[Tuple[str, str, _Line]] = []
    subs: List[Tuple[str, str, _Line]] = []

    for line in body:
        text = _strip_bullet(line.text)
        text = _strip_trailing_period(text)
        text = text.strip()
        if not text:
            continue
        m = _AGENT_LINE_RE.match(text)
        if not m:
            # Try the legacy form: "name is path/with/slashes"
            m2 = re.match(
                r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s+(?:is|are)\s+(.+?)\s*$",
                text,
            )
            if not m2:
                raise ParseError(
                    "expected 'Name is a <role>.' or "
                    "'Name is an office at <path>.'",
                    path=path,
                    line_no=line.no,
                    snippet=line.text,
                )
            agent_name = m2.group(1)
            rest = m2.group(2).strip()
            # Treat as a sub-office path (legacy network.md form).
            subs.append((agent_name, rest, line))
            continue

        agent_name = m.group(1)
        rest = m.group(2).strip()

        # Sub-office form: "office at <path>"
        sub_m = re.match(r"^office\s+at\s+(.+)$", rest, re.IGNORECASE)
        if sub_m:
            subs.append((agent_name, sub_m.group(1).strip(), line))
            continue

        # Plain role: "an editor", "a writer", etc. The article was
        # consumed by the regex (\s+an?\s+), so ``rest`` is the role
        # word(s). For now we accept a single identifier.
        if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", rest):
            raise ParseError(
                f"expected a single-word role name, got {rest!r}",
                path=path,
                line_no=line.no,
                snippet=line.text,
            )
        leaves.append((agent_name, rest, line))

    return leaves, subs


# ── Connections ────────────────────────────────────────────────────────


_POSSESSIVE_RE = re.compile(
    r"""^\s*
    ([A-Za-z_][A-Za-z0-9_]*)        # sender name
    \s*'s\s+
    ([A-Za-z_][A-Za-z0-9_]*)        # sender port
    \s+(is|are)\s+
    (.+?)                           # recipient list
    \s*$""",
    re.VERBOSE,
)


def _parse_destination(
    text: str,
    *,
    outputs: Tuple[str, ...],
    path: Optional[Path],
    line_no: int,
    snippet: str,
) -> Endpoint:
    """Parse one destination phrase into an ``Endpoint``.

    Three shapes are accepted:

    * ``name's port``       → ``Endpoint(name, port)`` — explicit named
                              port on a sub-office or some other agent.
    * ``name`` where ``name`` is a declared output of this office
                            → ``Endpoint("external", name)`` — the
                              office boundary.
    * ``name`` (anything else)
                            → ``Endpoint(name, IMPLICIT_INPORT)`` — a
                              leaf agent or sink with the implicit
                              single inport.
    """
    text = text.strip()
    m = re.match(
        r"^([A-Za-z_][A-Za-z0-9_]*)\s*'s\s+([A-Za-z_][A-Za-z0-9_]*)\s*$",
        text,
    )
    if m:
        return Endpoint(name=m.group(1), port=m.group(2))
    if re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", text):
        if text in outputs:
            return Endpoint(name=EXTERNAL, port=text)
        return Endpoint(name=text, port=IMPLICIT_INPORT)
    raise ParseError(
        f"expected a destination (a name or 'name\\'s port'), got {text!r}",
        path=path,
        line_no=line_no,
        snippet=snippet,
    )


def _split_recipients(
    text: str, path: Optional[Path], line_no: int, snippet: str
) -> List[str]:
    """Split a recipient list like ``X, Y and Z`` into ``["X","Y","Z"]``.

    Accepts: ``X``, ``X and Y``, ``X, Y``, ``X, Y and Z``, ``X, Y, Z``.
    """
    text = text.strip()
    # Replace ' and ' with ', ' so the rest is a simple comma split.
    # Be careful: only at top level.
    parts = re.split(r"\s+and\s+", text, flags=re.IGNORECASE)
    # Now each part may contain commas.
    out: List[str] = []
    for p in parts:
        for q in _split_top_level(p, ","):
            q = q.strip()
            if q:
                out.append(q)
    if not out:
        raise ParseError(
            "expected one or more recipients after 'is'/'are'",
            path=path,
            line_no=line_no,
            snippet=snippet,
        )
    return out


def _parse_connections_section(
    body: List[_Line],
    *,
    inputs: Tuple[str, ...],
    outputs: Tuple[str, ...],
    path: Optional[Path],
) -> List[ConnectionStmt]:
    """Parse each connection line into one ConnectionStmt.

    Senders matching declared ``inputs`` are normalised to
    ``Endpoint("external", <input_name>)``; destinations matching
    declared ``outputs`` are normalised to
    ``Endpoint("external", <output_name>)``. After this pass the
    boundary is uniformly represented and the compiler does not
    need to special-case it.
    """
    stmts: List[ConnectionStmt] = []
    for line in body:
        text = _strip_bullet(line.text)
        text = _strip_trailing_period(text)
        text = text.strip()
        if not text:
            continue
        m = _POSSESSIVE_RE.match(text)
        if not m:
            raise ParseError(
                "expected '<sender>'s <port> is/are <recipient(s)>'",
                path=path,
                line_no=line.no,
                snippet=line.text,
            )
        sender = m.group(1)
        sender_port = m.group(2)
        # m.group(3) is "is" or "are" — currently unused (recipients
        # parser handles both singular and plural forms).
        recipient_list = m.group(4)

        # Build the source Endpoint, normalising boundary inputs.
        if sender in inputs:
            source = Endpoint(name=EXTERNAL, port=sender)
        else:
            source = Endpoint(name=sender, port=sender_port)

        # Build the destination Endpoints, normalising boundary outputs.
        destinations = tuple(
            _parse_destination(
                r,
                outputs=outputs,
                path=path,
                line_no=line.no,
                snippet=line.text,
            )
            for r in _split_recipients(
                recipient_list, path, line.no, line.text
            )
        )
        stmts.append(
            ConnectionStmt(source=source, destinations=destinations)
        )
    return stmts


# ── Top-level entry point ──────────────────────────────────────────────


def parse_office_dir(office_dir: Path) -> OfficeSpec:
    """Parse an office directory into an ``OfficeSpec``.

    Parameters
    ----------
    office_dir
        Path to a directory containing ``office.md`` (or, for
        legacy support, ``network.md``).

    Returns
    -------
    OfficeSpec
        A fully validated spec. Every entry in ``spec.agents`` is a
        uniform ``RoleRef``; the role library decides whether each
        one resolves to a leaf agent or a sub-office.

    Raises
    ------
    ParseError
        On any syntactic problem in office.md. The error carries the
        file, the line number, and a snippet of the offending line.
    FileNotFoundError
        If ``office_dir`` does not exist or has no ``office.md`` /
        ``network.md`` file.
    """
    office_dir = Path(office_dir)
    if not office_dir.is_dir():
        raise FileNotFoundError(f"{office_dir} is not a directory")

    md_path = office_dir / "office.md"
    if not md_path.exists():
        md_path = office_dir / "network.md"
    if not md_path.exists():
        raise FileNotFoundError(
            f"{office_dir} has no office.md or network.md"
        )

    text = md_path.read_text(encoding="utf-8")
    lines = _enumerate_lines(text)
    sections = _split_sections(lines, md_path)

    return _build_office_spec(sections, office_dir, md_path)


def _build_office_spec(
    sections: List[_Section],
    office_dir: Path,
    md_path: Path,
) -> OfficeSpec:
    # Group sections by label (keeping order; later duplicates win
    # would be a silent bug, so we surface duplicates).
    seen_labels: Dict[str, _Section] = {}
    for sec in sections:
        if sec.label in seen_labels:
            raise ParseError(
                f"section {sec.label!r} appears twice",
                path=md_path,
                line_no=sec.header.no,
                snippet=sec.header.text,
            )
        seen_labels[sec.label] = sec

    if "office_header" not in seen_labels:
        raise ParseError(
            "missing '# Office: <name>' header",
            path=md_path,
            line_no=1,
            snippet=lines_or_blank(md_path),
        )

    office_name = seen_labels["office_header"].header.text.strip()

    # Inputs / Outputs (optional — empty in closed offices).
    inputs: Tuple[str, ...] = ()
    outputs: Tuple[str, ...] = ()
    if "inputs" in seen_labels:
        inputs, _ = _parse_name_list(
            seen_labels["inputs"].body, md_path, "Inputs"
        )
    if "outputs" in seen_labels:
        outputs, _ = _parse_name_list(
            seen_labels["outputs"].body, md_path, "Outputs"
        )

    # Sources / Sinks.
    sources: Tuple[SourceSpec, ...] = ()
    sinks: Tuple[SinkSpec, ...] = ()
    if "sources" in seen_labels:
        items = _parse_decl_section(
            seen_labels["sources"].body, md_path, "Sources"
        )
        sources = tuple(SourceSpec(name=n, args=a) for n, a, _, _ in items)
    if "sinks" in seen_labels:
        items = _parse_decl_section(
            seen_labels["sinks"].body, md_path, "Sinks"
        )
        sinks = tuple(SinkSpec(name=n, args=a) for n, a, _, _ in items)

    # Agents — leaf agents and sub-offices share one section. Both
    # become RoleRefs; only sub-office refs carry a path. The parser
    # does NOT open any role file or sub-office directory — port
    # shapes are the library's job, sub-office bodies are Layer 5's
    # job.
    agent_entries: List[RoleRef] = []
    if "agents" in seen_labels:
        leaves, subs = _parse_agents_section(
            seen_labels["agents"].body, md_path
        )
        for agent_name, role_name, _line in leaves:
            agent_entries.append(
                RoleRef(agent_name=agent_name, role_name=role_name)
            )
        for sub_name, sub_path, _line in subs:
            # role_name = the trailing path component, so the library
            # can register the sub-office under a stable identifier.
            # Layer 5 reads `path` to recursively parse the office.
            role_name = Path(sub_path).name or sub_path
            agent_entries.append(
                RoleRef(
                    agent_name=sub_name,
                    role_name=role_name,
                    path=sub_path,
                )
            )

    agents: Tuple[RoleRef, ...] = tuple(agent_entries)

    # Connections.
    connections: Tuple[ConnectionStmt, ...] = ()
    if "connections" in seen_labels:
        connections = tuple(
            _parse_connections_section(
                seen_labels["connections"].body,
                inputs=inputs,
                outputs=outputs,
                path=md_path,
            )
        )

    return OfficeSpec(
        name=office_name,
        inputs=inputs,
        outputs=outputs,
        sources=sources,
        sinks=sinks,
        agents=agents,
        connections=connections,
    )


def lines_or_blank(path: Path) -> str:
    """First line of ``path``, or '' on any error. Used in error formatting."""
    try:
        with path.open(encoding="utf-8") as fh:
            return fh.readline().rstrip("\n")
    except Exception:
        return ""
