"""Read the front matter of a role, source or sink (spec section 4.4).

The front matter is a few ``key: value`` lines between ``---`` lines: at
the top of a ``.md`` file, or at the top of a ``.py`` file's module
docstring. It is read only by Python and never becomes part of a prompt::

    ---
    emits: whether a news article is on the topic
    in: title, text
    out: on_topic (yes | no)
    ---

Keys (all optional; spec Principle 6, guardrails are recommended, never
required):

- ``emits:`` one line, shown by ``dsl roles``;
- ``kind:`` ``author``; absent means annotator;
- ``needs:`` the packages a Python file imports;
- ``in:`` the fields the role reads, checked before the role is called;
- ``out:`` the fields it returns, checked on every reply; or ``same as in``
  for an author that passes its input on unchanged.

  A field in ``in:`` or ``out:`` may say what it holds, in parentheses:
  values, ``verdict (publish | revise)``; a number, ``price (number)``,
  ``score (0..10)``, ``count (integer, >= 1)``; or text,
  ``reply (text, at most 600 chars)``;
- ``out if <field> is <value>:`` further fields of the messages whose
  ``<field>`` has that value (an author whose messages differ).

The old keys (``outboxes``, ``inboxes``, ``adds``, ``contract``, ``AI``)
are reported with what replaces them. Any other key is an error naming
the nearest known one. This module never imports or runs the file.
"""

from __future__ import annotations

import ast
import difflib
import re
from dataclasses import dataclass
from pathlib import Path

_KEYS = ("emits", "kind", "needs", "in", "out")
_OLD_KEYS = {
    "outboxes": "a role has one outbox; a decision field and a router replace named outboxes",
    "inboxes": "a role has one inbox",
    "adds": "write the fields under out:",
    "contract": "write the fields under out:",
    "ai": "choose the model in the office file: Name: role(ai=\"...\")",
}
_IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\Z")
_FIELD = re.compile(r"([A-Za-z_][A-Za-z0-9_]*)\s*(?:\((.*)\))?\Z")
_OUT_IF = re.compile(r"out\s+if\s+([A-Za-z_][A-Za-z0-9_]*)\s+is\s+(\S+)\Z", re.IGNORECASE)


class FrontMatterError(Exception):
    """Front matter that does not follow spec section 4.4."""

    def __init__(self, line: int, message: str) -> None:
        self.line = line
        self.message = message
        super().__init__(f"front matter line {line}: {message}")


@dataclass(frozen=True)
class Field:
    """One field in ``in:`` or ``out:``, and what it may hold.

    At most one of two kinds of constraint:

    - ``values``: the named values it may take (``yes | no``);
    - ``type`` (``number``, ``integer`` or ``text``) with, for a number,
      inclusive bounds ``low``/``high``, and for text, ``max_chars``.

    A field with neither may hold anything.
    """

    name: str
    values: tuple[str, ...] = ()
    type: str | None = None
    low: float | None = None
    high: float | None = None
    max_chars: int | None = None

    def constraint(self) -> str:
        """What is inside the parentheses, as it would be written; '' if nothing."""
        if self.values:
            return " | ".join(self.values)
        if self.type is None:
            return ""
        parts = [self.type]
        if self.low is not None and self.high is not None:
            parts.append(f"{_num(self.low)}..{_num(self.high)}")
        elif self.low is not None:
            parts.append(f">= {_num(self.low)}")
        elif self.high is not None:
            parts.append(f"<= {_num(self.high)}")
        if self.max_chars is not None:
            parts.append(f"at most {self.max_chars} chars")
        return ", ".join(parts)

    def __str__(self) -> str:
        inside = self.constraint()
        return f"{self.name} ({inside})" if inside else self.name


def _num(x: float) -> str:
    """3.0 as 3, 2.5 as 2.5."""
    return str(int(x)) if float(x).is_integer() else str(x)


@dataclass(frozen=True)
class Conditional:
    """An ``out if <field> is <value>:`` line."""

    field: str
    value: str
    fields: tuple[Field, ...]


@dataclass(frozen=True)
class FrontMatter:
    """What a front-matter block declares, and the text after it.

    ``inputs`` and ``outputs`` are None when the block has no ``in:`` or
    ``out:`` line: the role accepts any object, and the checks that need
    the declaration are skipped (spec 4.4).
    """

    emits: str | None = None
    kind: str = "annotator"
    needs: tuple[str, ...] = ()
    #: The names in ``in:``; ``input_fields`` has what each may hold.
    inputs: tuple[str, ...] | None = None
    outputs: tuple[Field, ...] | None = None
    input_fields: tuple[Field, ...] | None = None
    same_as_in: bool = False
    conditionals: tuple[Conditional, ...] = ()
    #: For a .md role, the prompt: exactly the text after the block.
    body: str = ""

    @property
    def is_author(self) -> bool:
        return self.kind == "author"


# ── Values ─────────────────────────────────────────────────────────────────


def _split_top(text: str) -> list[str]:
    """Split on commas that are not inside parentheses."""
    parts: list[str] = []
    depth = 0
    current = ""
    for ch in text:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if ch == "," and depth == 0:
            parts.append(current)
            current = ""
        else:
            current += ch
    parts.append(current)
    return [p.strip() for p in parts if p.strip()]


def _names(value: str, line: int, *, fields: bool) -> tuple[str, ...]:
    names = tuple(n.strip() for n in value.split(",") if n.strip())
    for name in names:
        if fields and not _IDENT.match(name):
            raise FrontMatterError(line, f"{name!r} in in: is not a field name.")
    return names


_TYPES = ("number", "integer", "text")
_NUMBER = r"-?\d+(?:\.\d+)?"
_RANGE = re.compile(rf"({_NUMBER})\s*\.\.\s*({_NUMBER})\Z")
_BOUND = re.compile(rf"(>=|<=)\s*({_NUMBER})\Z")
_LENGTH = re.compile(r"at\s+most\s+(\d+)\s+(?:chars?|characters?)\Z", re.IGNORECASE)
_FORMS = ("values like (yes | no), or number, integer, text, 0..10, >= 0, <= 100, "
          "at most 600 chars")


def _constraint(name: str, inside: str, part: str, line: int) -> Field:
    """The Field for ``name (inside)``.

    ``|`` means named values, as before. Otherwise a comma-separated list
    of terms: a type, a range or bound (a number), a length (text). A
    single word that is not a type is one named value, as it always was.
    """
    single = inside.strip()
    if "|" in inside or (single not in _TYPES and (
            _IDENT.match(single) or re.fullmatch(_NUMBER, single))):
        values = tuple(v.strip() for v in inside.split("|"))
        if not all(values):
            raise FrontMatterError(line, f"an empty value in {part!r}.")
        return Field(name, values)

    type_: str | None = None
    low: float | None = None
    high: float | None = None
    max_chars: int | None = None
    for term in (t.strip() for t in inside.split(",")):
        rng, bound, length = _RANGE.match(term), _BOUND.match(term), _LENGTH.match(term)
        if term in _TYPES:
            if type_ is not None:
                raise FrontMatterError(line, f"{part!r} gives two types; choose one.")
            type_ = term
        elif rng:
            low, high = float(rng.group(1)), float(rng.group(2))
            if low > high:
                raise FrontMatterError(line, f"in {part!r} the range runs backwards.")
        elif bound:
            if bound.group(1) == ">=":
                low = float(bound.group(2))
            else:
                high = float(bound.group(2))
        elif length:
            max_chars = int(length.group(1))
        else:
            raise FrontMatterError(
                line, f"{term!r} in {part!r} is not something a field can hold. "
                f"In parentheses: {_FORMS}."
            )
    numeric = low is not None or high is not None
    if numeric and max_chars is not None:
        raise FrontMatterError(line, f"{part!r} is a number and text at once.")
    if numeric:
        if type_ == "text":
            raise FrontMatterError(line, f"{part!r}: text cannot have a range; did you mean number?")
        type_ = type_ or "number"
    if max_chars is not None:
        if type_ not in (None, "text"):
            raise FrontMatterError(line, f"{part!r}: a {type_} has no length; did you mean text?")
        type_ = "text"
    if type_ == "integer":
        for bound_value in (low, high):
            if bound_value is not None and not bound_value.is_integer():
                raise FrontMatterError(line, f"{part!r}: an integer's bounds are whole numbers.")
    return Field(name, type=type_, low=low, high=high, max_chars=max_chars)


def _fields(value: str, line: int, key: str = "out") -> tuple[Field, ...]:
    fields: list[Field] = []
    for part in _split_top(value):
        m = _FIELD.match(part)
        if not m:
            if key == "in" and "(" not in part:
                raise FrontMatterError(line, f"{part!r} in in: is not a field name.")
            raise FrontMatterError(
                line, f"{part!r} is not a field, or a field with values like 'verdict (yes | no)'."
            )
        name, inside = m.group(1), m.group(2)
        if any(f.name == name for f in fields):
            raise FrontMatterError(line, f"{name!r} is listed twice.")
        fields.append(Field(name) if inside is None else _constraint(name, inside, part, line))
    return tuple(fields)


# ── The block ──────────────────────────────────────────────────────────────


def _split_block(text: str) -> tuple[list[str] | None, str, int]:
    """(block lines or None, text after the block, line number of the first block line)."""
    lines = text.splitlines(keepends=True)
    start = 0
    while start < len(lines) and not lines[start].strip():
        start += 1
    if start >= len(lines) or lines[start].strip() != "---":
        return None, text, 0
    for end in range(start + 1, len(lines)):
        if lines[end].strip() == "---":
            block = [ln.rstrip("\n") for ln in lines[start + 1 : end]]
            return block, "".join(lines[end + 1 :]), start + 2
    raise FrontMatterError(start + 1, "the front matter starts with --- but never ends.")


def parse_front_matter(text: str) -> FrontMatter:
    """Parse the front matter at the top of ``text`` (a .md file or a docstring)."""
    block, body, first = _split_block(text)
    if block is None:
        return FrontMatter(body=text)

    found: dict[str, str] = {}
    at: dict[str, int] = {}
    conditionals: list[Conditional] = []
    conditional_lines: list[int] = []
    for offset, raw in enumerate(block):
        line = first + offset
        code = raw.strip()
        if not code:
            continue
        key, colon, value = code.partition(":")
        if not colon:
            raise FrontMatterError(line, f"expected 'key: value', got {code!r}.")
        key, value = key.strip(), value.strip()
        out_if = _OUT_IF.match(key)
        if out_if:
            conditionals.append(Conditional(out_if.group(1), out_if.group(2), _fields(value, line)))
            conditional_lines.append(line)
            continue
        low = key.lower()
        if low in _OLD_KEYS:
            raise FrontMatterError(line, f"'{key}:' is from the old form; {_OLD_KEYS[low]}.")
        if low not in _KEYS:
            near = difflib.get_close_matches(low, _KEYS, n=1)
            hint = f" Did you mean '{near[0]}:'?" if near else ""
            raise FrontMatterError(line, f"unknown key '{key}:'.{hint}")
        if low in found:
            raise FrontMatterError(line, f"'{low}:' is given twice.")
        found[low] = value
        at[low] = line

    kind = found.get("kind", "annotator").lower()
    if kind not in ("annotator", "author"):
        raise FrontMatterError(
            at["kind"], f"kind: is 'author' (or absent for an annotator), not {kind!r}."
        )

    out = found.get("out")
    same_as_in = out is not None and out.lower() == "same as in"
    outputs = None if out is None or same_as_in else _fields(out, at["out"])

    listed = {f.name: f.values for f in outputs or ()}
    for c, line in zip(conditionals, conditional_lines):
        if c.field not in listed or c.value not in listed[c.field]:
            raise FrontMatterError(
                line,
                f"'out if {c.field} is {c.value}' needs '{c.field}' listed on the out: "
                f"line with the value '{c.value}'.",
            )

    input_fields = _fields(found["in"], at["in"], key="in") if "in" in found else None
    return FrontMatter(
        emits=found.get("emits"),
        kind=kind,
        needs=_names(found.get("needs", ""), at.get("needs", first), fields=False),
        inputs=None if input_fields is None else tuple(f.name for f in input_fields),
        outputs=outputs,
        input_fields=input_fields,
        same_as_in=same_as_in,
        conditionals=tuple(conditionals),
        body=body,
    )


def read_front_matter(path: Path) -> FrontMatter:
    """The front matter of a ``.md`` file, or of a ``.py`` file's docstring.

    A ``.py`` file is parsed, never imported. Its ``body`` is empty.
    """
    text = path.read_text(encoding="utf-8")
    if path.suffix != ".py":
        return parse_front_matter(text)
    try:
        doc = ast.get_docstring(ast.parse(text), clean=True)
    except SyntaxError as exc:
        raise FrontMatterError(0, f"{path.name} is not valid Python: {exc.msg}") from None
    fm = parse_front_matter(doc or "")
    return FrontMatter(
        emits=fm.emits, kind=fm.kind, needs=fm.needs, inputs=fm.inputs,
        outputs=fm.outputs, input_fields=fm.input_fields, same_as_in=fm.same_as_in,
        conditionals=fm.conditionals,
    )
