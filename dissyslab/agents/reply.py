"""Checking a role's reply against its front matter (spec section 4.5).

Two kinds of role, two checks:

- an **annotator** returns one object; its fields are added to the
  incoming message, which goes on as one message (a *map*);
- an **author** returns a list of objects, each sent as a new message,
  zero or more (a *flat-map*).

An English role's reply is text: it is parsed as one JSON value, after
unwrapping a single code fence if the model put one around it. A Python
role's reply is already a dict or a list and is checked the same way.

The result is either ``Accepted`` -- the messages to send, and the names
of any fields the role returned without declaring them, which are dropped
and counted -- or ``Rejected`` with the reason. A rejected reply costs
that one message; the agent reports it and carries on.

Everything here is a pure function of the reply, the front matter and the
incoming message: no threads, no model, nothing hidden.
"""

from __future__ import annotations

import difflib
import json
import math
from dataclasses import dataclass
from typing import Any

from dissyslab.office.frontmatter import Field, FrontMatter

Message = dict[str, Any]


@dataclass(frozen=True)
class Accepted:
    """The reply fits: these messages go out; these fields were dropped."""

    messages: tuple[Message, ...]
    dropped: tuple[str, ...] = ()


@dataclass(frozen=True)
class Rejected:
    """The reply does not fit the role's front matter, and why."""

    reason: str


Result = Accepted | Rejected


# ── Shared steps ───────────────────────────────────────────────────────────


def parse_reply(reply: Any) -> Any:
    """A model's text reply as one JSON value; any other reply unchanged.

    One code fence (```json ... ``` or ``` ... ```) around the whole reply
    is removed first. Raises ``ValueError`` if the text is not JSON.
    """
    if not isinstance(reply, str):
        return reply
    text = reply.strip()
    if text.startswith("```") and text.endswith("```") and text.count("```") == 2:
        text = text[3:-3]
        first, newline, rest = text.partition("\n")
        if newline and first.strip().isalpha():  # the "json" after the fence
            text = rest
    return json.loads(text)


def written(value: Any) -> str:
    """A value as written in front matter: true, false, 3, or the string."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    return value if isinstance(value, str) else json.dumps(value)


def _shown(value: Any) -> str:
    """A value for an error message: short, and saying what it is."""
    if isinstance(value, str):
        text = value if len(value) <= 40 else value[:37] + "..."
        return f"the text {text!r}"
    return repr(written(value)) if isinstance(value, (bool, int, float)) else type(value).__name__


def _holds(f: Field, value: Any) -> str | None:
    """Why ``value`` is not what ``f`` says it holds, or None if it is."""
    if f.values:
        got = written(value)
        if got in f.values:
            return None
        near = difflib.get_close_matches(got, f.values, n=1)
        hint = f" (closest: {near[0]!r})" if near else ""
        return f"{f.name!r} is {got!r}, which is not one of {', '.join(f.values)}{hint}."
    if f.type in ("number", "integer"):
        # bool is an int in Python; true is not a number in a contract.
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return f"{f.name!r} is {_shown(value)}, not a number."
        if not math.isfinite(value):
            return f"{f.name!r} is {value!r}, not a finite number."
        if f.type == "integer" and not float(value).is_integer():
            return f"{f.name!r} is {value!r}, not a whole number."
        # Written as `not (a <= b)` so that a NaN could never pass.
        if f.low is not None and not (value >= f.low):
            return f"{f.name!r} is {written(value)}, below its range ({f.constraint()})."
        if f.high is not None and not (value <= f.high):
            return f"{f.name!r} is {written(value)}, above its range ({f.constraint()})."
        return None
    if f.type == "text":
        if not isinstance(value, str):
            return f"{f.name!r} is {_shown(value)}, not text."
        if f.max_chars is not None and len(value) > f.max_chars:
            return (f"{f.name!r} is {len(value)} characters long; "
                    f"at most {f.max_chars} are allowed.")
    return None


def _check_fields(obj: Message, fields: tuple[Field, ...], what: str = "reply") -> str | None:
    """Every field present, holding what it declares. The problem, or None.

    ``what`` names the object in the message: "reply" for ``out:``,
    "message" for ``in:``.
    """
    for f in fields:
        if f.name not in obj:
            return f"the {what} has no field {f.name!r}."
        problem = _holds(f, obj[f.name])
        if problem:
            return problem
    return None


def check_incoming(msg: Message, fm: FrontMatter) -> str | None:
    """Why ``msg`` does not fit the role's ``in:``, or None if it does.

    Checked before the role is called, so a model never sees a message its
    role did not declare it can take. Without ``in:`` nothing is checked.
    ``in:`` does not trim the message: the role still receives all of it.
    """
    if fm.input_fields is None:
        return None
    return _check_fields(msg, fm.input_fields, what="message")


def _declared(obj: Message, fields: tuple[Field, ...]) -> tuple[Message, tuple[str, ...]]:
    """(the declared fields of ``obj``, the names of the others, which are dropped)."""
    names = {f.name for f in fields}
    kept = {k: v for k, v in obj.items() if k in names}
    dropped = tuple(k for k in obj if k not in names)
    return kept, dropped


# ── Annotators ─────────────────────────────────────────────────────────────


def check_annotator_reply(reply: Any, fm: FrontMatter, incoming: Message) -> Result:
    """Check an annotator's reply and add its fields to ``incoming``.

    The reply must be one object with every field in ``out:``, each
    holding what it declares (a listed value, a number in range, text no
    longer than its limit). Undeclared fields are dropped. An annotator
    only adds: a field already in the message may not be given a different
    value. Without ``out:`` nothing is checked or dropped (spec 4.4).
    """
    try:
        obj = parse_reply(reply)
    except ValueError:
        return Rejected("the reply is not JSON.")
    if not isinstance(obj, dict):
        return Rejected(f"an annotator returns one JSON object, not {type(obj).__name__}.")

    dropped: tuple[str, ...] = ()
    if fm.outputs is not None:
        problem = _check_fields(obj, fm.outputs)
        if problem:
            return Rejected(problem)
        obj, dropped = _declared(obj, fm.outputs)

    for key, value in obj.items():
        if key in incoming and incoming[key] != value:
            return Rejected(
                f"the reply would change {key!r}, which is already in the message; "
                "an annotator only adds fields."
            )
    return Accepted(({**incoming, **obj},), dropped)


# ── Authors ────────────────────────────────────────────────────────────────


def _fields_for(obj: Message, fm: FrontMatter) -> tuple[Field, ...]:
    """The ``out:`` fields plus those of every ``out if`` line ``obj`` meets."""
    fields = fm.outputs or ()
    for c in fm.conditionals:
        if c.field in obj and written(obj[c.field]) == c.value:
            fields = fields + c.fields
    return fields


def check_author_reply(reply: Any, fm: FrontMatter) -> Result:
    """Check an author's reply: a list of complete new messages.

    Each object must have the fields of ``out:`` and of every ``out if``
    line whose condition it meets; undeclared fields are dropped. With
    ``out: same as in``, or no ``out:``, the objects are sent as they are.
    The empty list sends nothing.
    """
    try:
        value = parse_reply(reply)
    except ValueError:
        return Rejected("the reply is not JSON.")
    if not isinstance(value, list):
        return Rejected(f"an author returns a JSON list of objects, not {type(value).__name__}.")

    messages: list[Message] = []
    dropped: list[str] = []
    for i, obj in enumerate(value):
        if not isinstance(obj, dict):
            return Rejected(f"item {i} of the reply is {type(obj).__name__}, not an object.")
        if fm.outputs is None:  # no out:, or out: same as in
            messages.append(obj)
            continue
        fields = _fields_for(obj, fm)
        problem = _check_fields(obj, fields)
        if problem:
            return Rejected(f"item {i}: {problem}")
        kept, extra = _declared(obj, fields)
        messages.append(kept)
        dropped.extend(k for k in extra if k not in dropped)
    return Accepted(tuple(messages), tuple(dropped))
