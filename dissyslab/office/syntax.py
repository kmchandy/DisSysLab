"""Read an office file written in the line form (spec section 3.1).

Two kinds of line, told apart by their symbol::

    name: kind(arg=value, ...)      a declaration (sources:, sinks:, agents:)
    a -> b -> c, d                  connections (connections:)

plus the section headings and, for an office meant to sit inside another,
the names under ``inputs:`` and ``outputs:``.

**Forgiving of** spacing and indentation, blank lines, ``#`` comments
(outside quotes), either quote style, ``true`` or ``True``, a trailing
comma or period, ``->`` or ``→``, ``kind`` or ``kind()``, the case of
section headings, and a declaration spread over several lines while a
parenthesis or bracket is open.

**Not forgiving of** anything else: each problem is an ``OfficeSyntaxError``
naming the line and, where it can, the nearest word. The parser never
guesses. Arguments are read with ``ast.literal_eval``, never executed.

This module knows nothing about which kinds exist or what ports they have;
those are checked later, by ``dsl check``.
"""

from __future__ import annotations

import ast
import difflib
import re
from pathlib import Path
from typing import Any

from dissyslab.office.model import (
    SECTIONS,
    Connection,
    Declaration,
    OfficeFile,
    PortRef,
)

_IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\Z")
_HEADING = re.compile(r"([A-Za-z]+)\s*:\Z")
_OLD_FORM = re.compile(r"^[A-Za-z_]\w*('s\s|\s+(is|are)\s)")


class OfficeSyntaxError(Exception):
    """An office file that does not follow the line form."""

    def __init__(self, line: int, text: str, message: str) -> None:
        self.line = line
        self.text = text
        self.message = message
        super().__init__(f"line {line}: {message}\n    {text}")


# ── Lines ──────────────────────────────────────────────────────────────────


def _scan(text: str) -> tuple[str, int]:
    """Strip a ``#`` comment outside quotes; return (code, bracket depth change)."""
    depth = 0
    quote: str | None = None
    escaped = False
    for i, ch in enumerate(text):
        if quote:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == quote:
                quote = None
        elif ch in "'\"":
            quote = ch
        elif ch == "#":
            return text[:i], depth
        elif ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
    return text, depth


def _logical_lines(text: str) -> list[tuple[int, str]]:
    """Join continuation lines; drop comments and blanks. (line number, text)."""
    out: list[tuple[int, str]] = []
    pending = ""
    start = 0
    depth = 0
    for number, raw in enumerate(text.splitlines(), start=1):
        code, change = _scan(raw)
        if not pending and not code.strip():
            continue
        if not pending:
            start = number
        pending = f"{pending} {code.strip()}" if pending else code.strip()
        depth += change
        if depth <= 0:
            out.append((start, pending))
            pending, depth = "", 0
    if pending:
        out.append((start, pending))  # unbalanced; the line's own parse reports it
    return out


def _strip_end(code: str) -> str:
    """Drop one trailing period or comma (forgiven, spec 3.1)."""
    code = code.rstrip()
    if code.endswith((".", ",")):
        code = code[:-1].rstrip()
    return code


def _suggest(word: str, choices: Any) -> str:
    near = difflib.get_close_matches(word, list(choices), n=1)
    return f" Did you mean {near[0]!r}?" if near else ""


# ── Declarations ───────────────────────────────────────────────────────────


def _literal(node: ast.expr) -> Any:
    """A Python literal, with ``true``/``false`` read as booleans."""

    class _Booleans(ast.NodeTransformer):
        def visit_Name(self, n: ast.Name) -> ast.AST:
            if n.id in ("true", "false"):
                return ast.copy_location(ast.Constant(n.id == "true"), n)
            return n

    return ast.literal_eval(_Booleans().visit(node))


def _parse_call(text: str, line: int, raw: str) -> tuple[str, dict[str, Any]]:
    """``kind``, ``kind()`` or ``kind(a=1, b="x")`` -> (kind, args)."""
    text = text.strip()
    if _IDENT.match(text):
        return text, {}
    try:
        node = ast.parse(text, mode="eval").body
    except SyntaxError as exc:
        raise OfficeSyntaxError(line, raw, f"cannot read {text!r}: {exc.msg}.") from None
    if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name):
        raise OfficeSyntaxError(line, raw, f"expected kind or kind(name=value, ...), got {text!r}.")
    func: ast.Name = node.func
    if node.args:
        raise OfficeSyntaxError(
            line, raw, "arguments are named, as in a Python call: kind(name=value)."
        )
    args: dict[str, Any] = {}
    for kw in node.keywords:
        if kw.arg is None:
            raise OfficeSyntaxError(line, raw, "** is not allowed in an office file.")
        try:
            args[kw.arg] = _literal(kw.value)
        except ValueError:
            raise OfficeSyntaxError(
                line,
                raw,
                f"the value of {kw.arg!r} must be written out: a string in quotes, "
                "a number, true or false, or a list.",
            ) from None
    return func.id, args


def _parse_declaration(code: str, line: int, raw: str, section: str) -> Declaration:
    head, sep, rest = code.partition(":")
    if sep and _IDENT.match(head.strip()) and "(" not in head:
        name = head.strip()
        if name.lower() in SECTIONS:
            raise OfficeSyntaxError(
                line, raw, f"a section heading stands alone on its line: write '{name.lower()}:'."
            )
        kind, args = _parse_call(rest, line, raw)
    else:
        kind, args = _parse_call(code, line, raw)
        name = kind
    return Declaration(name=name, kind=kind, args=args, section=section, line=line)


# ── Connections ────────────────────────────────────────────────────────────


def _parse_endpoint(text: str, line: int, raw: str) -> PortRef:
    name, dot, port = text.strip().partition(".")
    if not _IDENT.match(name) or (dot and not _IDENT.match(port)):
        raise OfficeSyntaxError(
            line, raw, f"{text.strip()!r} is not a name or name.port."
        )
    return PortRef(name=name, port=port if dot else None)


def _parse_connections(code: str, line: int, raw: str) -> list[Connection]:
    groups = [g for g in code.replace("→", "->").split("->")]
    if len(groups) < 2 or any(not g.strip() for g in groups):
        raise OfficeSyntaxError(line, raw, "a connection is a -> b, with a name on each side.")
    parsed = [[_parse_endpoint(x, line, raw) for x in g.split(",")] for g in groups]
    for group in parsed[1:-1]:
        if len(group) > 1:
            raise OfficeSyntaxError(
                line, raw, "a list (a, b) may stand only at either end of a chain."
            )
    out: list[Connection] = []
    for senders, receivers in zip(parsed, parsed[1:]):
        for s in senders:
            for r in receivers:
                out.append(Connection(sender=s, receiver=r, line=line))
    return out


# ── The file ───────────────────────────────────────────────────────────────


def parse_office_text(text: str) -> OfficeFile:
    """Parse the text of an office file. Raises ``OfficeSyntaxError``."""
    raw_lines = text.splitlines()
    section: str | None = None
    found: dict[str, list[Any]] = {s: [] for s in SECTIONS}
    names: dict[str, int] = {}

    for line, joined in _logical_lines(text):
        raw = raw_lines[line - 1].strip()
        code = _strip_end(joined.replace("→", "->"))

        heading = _HEADING.match(code)
        if heading:
            word = heading.group(1).lower()
            if word not in SECTIONS:
                raise OfficeSyntaxError(
                    line, raw, f"no section called {word!r}.{_suggest(word, SECTIONS)}"
                )
            section = word
            continue

        head, colon, rest = code.partition(":")
        if colon and head.strip().lower() in SECTIONS and rest.strip():
            raise OfficeSyntaxError(
                line,
                raw,
                f"a section heading stands alone on its line: write "
                f"'{head.strip().lower()}:' and put each item on a line below it.",
            )

        if _OLD_FORM.match(code):
            raise OfficeSyntaxError(
                line,
                raw,
                "this looks like the old sentence form. Write declarations as "
                "'name: kind(args)' and connections as 'a -> b' (spec section 3.1).",
            )

        if section is None:
            raise OfficeSyntaxError(
                line, raw, "this line is not under any section (sources:, sinks:, agents:, ...)."
            )

        if section == "connections":
            if "->" not in code:
                raise OfficeSyntaxError(
                    line, raw, "under connections:, each line is a -> b."
                )
            found["connections"].extend(_parse_connections(code, line, raw))
            continue

        if "->" in code:
            raise OfficeSyntaxError(
                line, raw, f"connections go under connections:, not {section}:."
            )

        if section in ("inputs", "outputs"):
            for item in code.split(","):
                port = item.strip()
                if not _IDENT.match(port):
                    raise OfficeSyntaxError(line, raw, f"{port!r} is not a name.")
                if port in names:
                    raise OfficeSyntaxError(
                        line, raw, f"{port!r} is already declared on line {names[port]}."
                    )
                names[port] = line
                found[section].append(port)
            continue

        decl = _parse_declaration(code, line, raw, section)
        if decl.name in names:
            raise OfficeSyntaxError(
                line, raw, f"{decl.name!r} is already declared on line {names[decl.name]}."
            )
        names[decl.name] = line
        found[section].append(decl)

    for conn in found["connections"]:
        for end in (conn.sender, conn.receiver):
            if end.name not in names:
                raise OfficeSyntaxError(
                    conn.line,
                    raw_lines[conn.line - 1].strip(),
                    f"{end.name!r} is not declared.{_suggest(end.name, names)}",
                )

    return OfficeFile(
        inputs=tuple(found["inputs"]),
        outputs=tuple(found["outputs"]),
        sources=tuple(found["sources"]),
        sinks=tuple(found["sinks"]),
        agents=tuple(found["agents"]),
        connections=tuple(found["connections"]),
        names=names,
    )


def is_old_form(text: str) -> bool:
    """True if ``text`` is an office in the version 1 sentence form.

    The old form has sentences (``Alex is a writer.``, ``Alex's out is
    ...``) or a section heading with items on the same line
    (``Sources: bbc_world``). The new form has neither, so one such line
    decides it. ``dsl run`` and ``dsl check`` use this to send an office
    down the old path or the new one until the old path is removed
    (Phase 6b).
    """
    for _line, joined in _logical_lines(text):
        code = _strip_end(joined)
        if _OLD_FORM.match(code):
            return True
        head, colon, rest = code.partition(":")
        if colon and head.strip().lower() in ("sources", "sinks") and rest.strip():
            return True
    return False


def parse_office_file(path: Path) -> OfficeFile:
    """Parse ``path`` (an ``office.md``). Raises ``OfficeSyntaxError``."""
    return parse_office_text(path.read_text(encoding="utf-8"))
