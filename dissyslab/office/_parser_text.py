"""
Text-level utilities used by the office.md parser.

Two responsibilities:

1. **Line and section bookkeeping.** A ``_Line`` pairs a body of
   text with its 1-based source line number. ``_enumerate_lines``
   produces them. ``_split_sections`` groups lines into labelled
   sections — this is the boundary between "raw markdown" and
   "office.md grammar".

2. **Generic syntactic forms.** ``_split_top_level`` is a
   paren/quote-aware comma split. ``_parse_kw_args`` parses the
   contents of a ``(k=v, k=v)`` group via ``ast.literal_eval``.
   ``_parse_decl`` parses a ``name`` or ``name(k=v)`` declaration.

Nothing here knows what an "agent" or a "connection" is — those
concepts live in ``parser.py``. The split keeps text mechanics
separate from grammar semantics so each layer can be read and
maintained on its own.
"""
from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from dissyslab.office.parser_errors import ParseError


# Section names recognised at the document level. Keys are the
# user-typed forms (lower-cased for case-insensitive matching);
# values are the canonical labels the rest of the parser uses.
_SECTION_HEADERS: Dict[str, str] = {
    "office": "office_header",
    "network": "office_header",  # legacy network.md headers
    "inputs": "inputs",
    "outputs": "outputs",
    "sources": "sources",
    "sinks": "sinks",
    "agents": "agents",
    "offices": "agents",         # legacy network.md sub-offices section
    "connections": "connections",
    "role": "role_header",
}


# ── Lines ─────────────────────────────────────────────────────────────


@dataclass
class _Line:
    """A line of source paired with its 1-based line number."""

    no: int
    text: str

    @property
    def stripped(self) -> str:
        return self.text.strip()


def _enumerate_lines(text: str) -> List[_Line]:
    """Split ``text`` into ``_Line``s, line numbers starting at 1."""
    return [_Line(i, t) for i, t in enumerate(text.splitlines(), start=1)]


def _strip_trailing_period(s: str) -> str:
    s = s.rstrip()
    if s.endswith("."):
        s = s[:-1].rstrip()
    return s


def _strip_bullet(s: str) -> str:
    """Remove a leading ``- `` or ``* `` bullet, if present."""
    s2 = s.lstrip()
    if s2.startswith(("- ", "* ")):
        return s2[2:]
    return s


# ── Section splitting ─────────────────────────────────────────────────


@dataclass
class _Section:
    """One labelled section of an office.md file."""

    label: str            # canonical label, e.g. "agents"
    header: _Line         # the header line itself
    body: List[_Line]     # body lines, in order, blanks dropped


def _split_sections(
    lines: List[_Line], path: Optional[Path]
) -> List[_Section]:
    """Group lines into labelled sections.

    A section starts at a line of the form ``<Header>:`` whose
    header (case-folded, before the colon) is in ``_SECTION_HEADERS``,
    OR a line of the form ``# Office: name`` / ``# Network: name``
    / ``# Role: name`` (the markdown-style document header). Body
    lines run until the next section start. Blank lines are dropped
    from bodies but their line numbers remain assigned to following
    lines (we keep ``_Line.no`` from the original enumeration).
    """
    sections: List[_Section] = []
    current: Optional[_Section] = None

    for line in lines:
        s = line.stripped
        if not s:
            continue

        # Document header: "# Office: news_editorial"
        if s.startswith("#"):
            head = s.lstrip("#").strip()
            label, rest = _parse_doc_header(head, line, path)
            if label is not None:
                # Treat the document header as its own section so
                # parse_* helpers can read the office name.
                sec = _Section(
                    label=label,
                    header=_Line(no=line.no, text=rest),
                    body=[],
                )
                sections.append(sec)
                current = None
                continue
            # Any other ``#``-prefixed line is a comment. The grammar
            # itself does not need them, but Pat-facing office files
            # benefit from labels on the four edit slots (sources,
            # parallel thinkers, writer, sinks). Skipping comments at
            # the section-splitting level means they vanish before any
            # section body is parsed, so per-section parsers do not
            # need to know about them.
            continue

        # Body-style header: "Sources:"
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_ ]*?):\s*(.*)$", s)
        if m:
            head_raw = m.group(1).strip()
            head = head_raw.lower()
            after = m.group(2)
            if head in _SECTION_HEADERS:
                # Start a new section. Anything after the colon on
                # the same line is treated as the first body line.
                current = _Section(
                    label=_SECTION_HEADERS[head],
                    header=line,
                    body=[],
                )
                sections.append(current)
                if after.strip():
                    current.body.append(_Line(no=line.no, text=after))
                continue
            # The line looks like a section header but the name is
            # not one we recognise. If we are not already inside a
            # section, this is almost certainly a typo (``Source:``
            # for ``Sources:``). Surface a Pat-friendly diagnostic
            # with a "Did you mean?" suggestion against the real
            # section headers, rather than the generic
            # "unexpected text outside any section".
            if current is None:
                import difflib
                pat_facing = (
                    "Office", "Inputs", "Outputs", "Sources", "Sinks",
                    "Agents", "Connections",
                )
                matches = difflib.get_close_matches(
                    head_raw.title(),
                    list(pat_facing),
                    n=1,
                    cutoff=0.6,
                )
                parts = [
                    f"Unknown section header {head_raw + ':'!r}."
                ]
                if matches:
                    parts.append(
                        f"Did you mean {matches[0] + ':'!r}?"
                    )
                parts.append(
                    f"Valid section headers: "
                    f"{', '.join(h + ':' for h in pat_facing)}."
                )
                raise ParseError(
                    " ".join(parts),
                    path=path,
                    line_no=line.no,
                    snippet=line.text,
                )

        # If we get here, the line is body for the current section.
        if current is None:
            raise ParseError(
                f"unexpected text outside any section",
                path=path,
                line_no=line.no,
                snippet=line.text,
            )
        current.body.append(line)

    return sections


def _parse_doc_header(
    head: str, line: _Line, path: Optional[Path]
) -> Tuple[Optional[str], str]:
    """Parse '# Office: name' / '# Network: name' / '# Role: name'.

    Returns ``(label, name)`` or ``(None, '')`` if not a recognised
    document header.
    """
    m = re.match(
        r"^(Office|Network|Role)\s*:\s*(.+?)\s*$", head, re.IGNORECASE
    )
    if not m:
        return (None, "")
    kind = m.group(1).lower()
    name = m.group(2).strip()
    if not name:
        raise ParseError(
            f"# {m.group(1)}: header has empty name",
            path=path,
            line_no=line.no,
            snippet=line.text,
        )
    if kind in ("office", "network"):
        return ("office_header", name)
    return ("role_header", name)


def _join_continuations(body: List[_Line]) -> List[_Line]:
    """Fold multi-line declarations.

    A continuation is a line whose preceding line ended with ``,``.
    Used by the Sources/Sinks parser so that

        Sinks: console_printer,
               jsonl_recorder(path="x.jsonl")

    becomes one logical line. The folded line keeps the line number
    of the first physical line.
    """
    folded: List[_Line] = []
    for line in body:
        if folded and folded[-1].text.rstrip().endswith(","):
            prev = folded.pop()
            folded.append(
                _Line(no=prev.no, text=prev.text + " " + line.text)
            )
        else:
            folded.append(line)
    return folded


# ── Generic syntactic forms ───────────────────────────────────────────


def _split_top_level(s: str, delim: str = ",") -> List[str]:
    """Split ``s`` on ``delim`` ignoring delimiters inside brackets/quotes.

    Tracks nesting depth for ``()``, ``[]``, and ``{}`` so a literal
    list/dict/tuple can contain ``delim`` (typically ``,``) without
    being split. Also handles single and double quotes (no escape
    sequences inside — we never need them for this grammar).
    """
    parts: List[str] = []
    depth = 0
    in_quote: Optional[str] = None
    buf: List[str] = []
    OPENERS = "([{"
    CLOSERS = ")]}"
    for ch in s:
        if in_quote:
            buf.append(ch)
            if ch == in_quote:
                in_quote = None
            continue
        if ch in ("'", '"'):
            in_quote = ch
            buf.append(ch)
            continue
        if ch in OPENERS:
            depth += 1
            buf.append(ch)
            continue
        if ch in CLOSERS:
            depth -= 1
            buf.append(ch)
            continue
        if ch == delim and depth == 0:
            parts.append("".join(buf).strip())
            buf = []
            continue
        buf.append(ch)
    if buf:
        parts.append("".join(buf).strip())
    return [p for p in parts if p]


def _parse_kw_args(
    args_text: str, path: Optional[Path], line_no: int, snippet: str
) -> Tuple[Tuple[str, Any], ...]:
    """Parse ``key=val, key=val`` (the contents of a paren group).

    Each value is run through ``ast.literal_eval``, so it must be a
    Python literal: int, float, str, bool, None, or a tuple/list of
    those. Anything else (e.g., a bare identifier as a value) raises
    ``ParseError``.
    """
    args_text = args_text.strip()
    if not args_text:
        return ()
    out: List[Tuple[str, Any]] = []
    for piece in _split_top_level(args_text, ","):
        if "=" not in piece:
            raise ParseError(
                f"expected 'key=value' in arguments, got {piece!r}",
                path=path,
                line_no=line_no,
                snippet=snippet,
            )
        key, _, value = piece.partition("=")
        key = key.strip()
        value = value.strip()
        if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", key):
            raise ParseError(
                f"invalid argument name {key!r}",
                path=path,
                line_no=line_no,
                snippet=snippet,
            )
        try:
            parsed: Any = ast.literal_eval(value)
        except (SyntaxError, ValueError):
            raise ParseError(
                f"argument {key}={value!r} must be a Python literal "
                f"(string, number, True, False, or None)",
                path=path,
                line_no=line_no,
                snippet=snippet,
            )
        out.append((key, parsed))
    return tuple(out)


_NAME_AND_ARGS_RE = re.compile(
    r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*(?:\((.*)\))?\s*$"
)


def _parse_decl(
    text: str, path: Optional[Path], line_no: int, snippet: str
) -> Tuple[str, Tuple[Tuple[str, Any], ...]]:
    """Parse one ``name`` or ``name(k=v, k=v)`` declaration."""
    m = _NAME_AND_ARGS_RE.match(text.strip())
    if not m:
        raise ParseError(
            f"expected a name or name(...) declaration, got {text!r}",
            path=path,
            line_no=line_no,
            snippet=snippet,
        )
    name = m.group(1)
    args_text = m.group(2) or ""
    args = _parse_kw_args(args_text, path, line_no, snippet)
    return name, args


__all__ = [
    "_Line",
    "_NAME_AND_ARGS_RE",
    "_SECTION_HEADERS",
    "_Section",
    "_enumerate_lines",
    "_join_continuations",
    "_parse_decl",
    "_parse_doc_header",
    "_parse_kw_args",
    "_split_sections",
    "_split_top_level",
    "_strip_bullet",
    "_strip_trailing_period",
]
