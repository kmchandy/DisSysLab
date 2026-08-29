"""What ports a role has, read from the role rather than guessed at.

The problem this replaces
-------------------------
An agent's interface was never declared anywhere. For a prose role the
framework *inferred* it, by running a regular expression over English::

    If the item is relevant, send to keep. Otherwise send to discard.

Three consequences, and the third is the root of the other two:

1. ``office.md`` could not be checked by reading it. ``Screen is a
   relevance_filter.`` says nothing about Screen having an outbox
   called ``discard``, and finding out meant opening a file that might
   be inside the installed package.
2. Write ``send to `keep` `` -- backticks, as any careful writer does
   -- and the port was silently not created. The office checked clean
   and produced nothing, and no check could see it, because there was
   no declaration for the regex to disagree with.
3. A sub-office declares its interface (``Inputs:``/``Outputs:``) and a
   role did not. The language already had the concept; it was applied
   to one kind of agent and not the other.

Where a declaration lives
-------------------------
**A prose role declares in its front matter**, beside ``emits:``::

    ---
    emits: decides whether an item is worth passing on
    inboxes: in_
    outboxes: keep, discard
    ---

``inboxes:`` may be omitted and defaults to ``in_``, which is what all
but three roles have.

**A Python role has already declared**, in the ``AgentRoleEntry`` it
builds -- forty of the forty-seven shipped ones spell their ports as
literals there. Nothing was added to those files: this reads the call.
Where the ports are computed, module-level names are resolved; where
the role is built by a helper and nothing is readable, the module
docstring carries the same front matter as a prose role.

The fields a role adds
----------------------
``adds:`` is the same idea one level along, and it exists because the
same defect was found one level along::

    ---
    emits: adds a `summary` field -- one plain-English sentence
    outboxes: out
    adds: summary
    ---

An annotator exists to put a named field on the message. Until this
was declared, the role said so in prose -- *"Output. Return a single
JSON object containing every field of the input plus `summary`"* --
while the framework appended, as the last thing the model reads::

    Return JSON only, no explanation, no nested JSON:
    {"send_to": "<one of: out>", "text": "<content>"}

Two keys. Not `summary`. A model that obeys the last line returns
those two and the field the role is *for* never appears; a model that
obeys the role ignores the contract. Which one wins is up to the model,
and the twelve shipped annotators worked only because capable models
follow the longer, more specific block. That is not a guarantee, and it
is weakest on exactly the small local models a beginner is pointed at.

There was a second collision in the same two lines. ``text`` means the
*article body* in the input shape and the *role's output* in the
contract, so a model obeying the contract overwrote the body -- in
roles that promise, in the same prompt, to preserve every field.

With ``adds:`` declared the contract is generated from the declaration
and names exactly what the role produces::

    filter:      {"send_to": "<one of: keep, discard>"}
    summarizer:  {"send_to": "<one of: out>", "summary": "..."}

No generic content slot, so ``text`` never appears in a contract and
the collision cannot arise. The prose stops asserting the shape because
nothing needs it to.

Read, never imported
--------------------
Every path here is static. Importing a role to discover its ports would
execute code that arrived by being generated, during ``dsl check`` --
the one command that must be safe to run on something you do not trust.
``role_effects.py`` and W12 exist because we take that seriously, and
this must not undo it.
"""
from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Tuple

#: The inbox almost every role has, and the default when a prose role
#: does not say. Three roles differ -- synchronizer, select and gate --
#: and none of them is a file.
DEFAULT_INBOX = "in_"

_FRONT_MATTER = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.S)


class PortDeclarationError(Exception):
    """A role file that does not say what its ports are."""


@dataclass(frozen=True)
class Ports:
    inboxes: Tuple[str, ...]
    outboxes: Tuple[str, ...]
    #: The fields this role puts on the message, in declared order.
    #:
    #: Empty for a role that only routes: a filter decides, it does not
    #: add. Non-empty for every annotator -- ``summarizer`` adds
    #: ``summary``, ``geolocator`` adds ``location`` -- which is the
    #: whole reason those roles exist.
    #:
    #: This is what lets the output contract be *generated* rather than
    #: written twice. See ``The fields a role adds`` below.
    adds: Tuple[str, ...] = ()


# ── prose roles ───────────────────────────────────────────────────────


def _front_matter(text: str) -> dict[str, str]:
    """The ``key: value`` block at the top of a file, if there is one."""
    m = _FRONT_MATTER.match(text)
    if not m:
        return {}
    out: dict[str, str] = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            out[key.strip()] = value.strip()
    return out


def _name_list(value: str) -> Tuple[str, ...]:
    """``keep, discard`` or ``[keep, discard]`` -> ``("keep", "discard")``.

    Order is preserved and duplicates are not removed silently: the
    runtime maps ``out_ports[i]`` to ``out_i``, so order is meaning,
    and a repeated name is a mistake worth seeing rather than tidying.
    """
    value = value.strip().strip("[]")
    return tuple(p.strip().strip("\"'") for p in value.split(",") if p.strip())


# ── Python roles ──────────────────────────────────────────────────────


def _module_literals(tree: ast.Module) -> dict[str, object]:
    """Module-level names bound to literals, for resolving references.

    ``out_ports=tuple(_STATUSES)`` is three of the shipped roles, and
    ``_STATUSES`` is a literal list six lines above. Resolving it costs
    a dictionary and saves editing three files to say what they already
    say.
    """
    out: dict[str, object] = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
            if isinstance(target, ast.Name):
                try:
                    out[target.id] = ast.literal_eval(node.value)
                except (ValueError, SyntaxError):
                    pass
    return out


def _ports_arg(node: ast.expr, literals: dict[str, object]) -> Tuple[str, ...] | None:
    """One `in_ports=` / `out_ports=` argument, if it can be read."""
    try:
        return tuple(str(p) for p in ast.literal_eval(node))
    except (ValueError, SyntaxError):
        pass
    # tuple(_STATUSES) / list(_STATUSES)
    if isinstance(node, ast.Call) and getattr(node.func, "id", "") in {"tuple", "list"}:
        if len(node.args) == 1:
            return _ports_arg(node.args[0], literals)
    if isinstance(node, ast.Name) and node.id in literals:
        value = literals[node.id]
        if isinstance(value, (list, tuple)):
            return tuple(str(p) for p in value)
    return None


def _from_agent_role_entry(
    tree: ast.Module, adds: Tuple[str, ...] = ()
) -> Ports | None:
    """Ports spelled in the ``AgentRoleEntry(...)`` the module builds.

    ``adds`` comes from the module docstring rather than the call:
    ``AgentRoleEntry`` has no field for it, a Python role's function
    can put anything on a message, and there is nothing static to read.
    A Python role that adds a field says so in its docstring front
    matter, exactly as a prose role does.
    """
    literals = _module_literals(tree)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if getattr(node.func, "id", "") != "AgentRoleEntry":
            continue
        kw = {k.arg: k.value for k in node.keywords if k.arg}
        ins = _ports_arg(kw["in_ports"], literals) if "in_ports" in kw else None
        outs = _ports_arg(kw["out_ports"], literals) if "out_ports" in kw else None
        if ins is not None and outs is not None:
            return Ports(ins, outs, adds)
    return None


def _docstring_front_matter(text: str) -> dict[str, str]:
    """Front matter inside the module docstring.

    The fallback for a role built by a helper, where nothing in the
    file spells the ports. Same keys as a prose role's, so there is one
    format to learn rather than two.
    """
    _, sep, after = text.partition('"""')
    return _front_matter(after.lstrip("\n")) if sep else {}


# ── the one entry point ───────────────────────────────────────────────


def read_ports(path: Path) -> Ports:
    """The ports a role declares. Raises when it declares none.

    Raising rather than guessing is the whole point. A role whose ports
    are unknown used to get whatever a regular expression found in its
    prose, which is how a missing declaration became a working office
    that dropped messages.
    """
    path = Path(path)
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise PortDeclarationError(f"{path.name}: cannot read ({exc})") from exc

    if path.suffix == ".py":
        try:
            tree = ast.parse(text)
        except SyntaxError as exc:
            raise PortDeclarationError(
                f"{path.name}: will not parse ({exc.msg} on line {exc.lineno})"
            ) from exc
        meta = _docstring_front_matter(text)
        adds = _name_list(meta.get("adds", ""))
        found = _from_agent_role_entry(tree, adds)
        if found is not None:
            return found
        if "outboxes" in meta:
            return Ports(
                _name_list(meta.get("inboxes", DEFAULT_INBOX)),
                _name_list(meta["outboxes"]),
                adds,
            )
        raise PortDeclarationError(
            f"{path.name} does not say what its ports are.\n"
            "  Either build an AgentRoleEntry with literal in_ports and\n"
            "  out_ports, or put them in the module docstring:\n"
            "      ---\n"
            "      inboxes: in_\n"
            "      outboxes: keep, discard\n"
            "      ---"
        )

    meta = _front_matter(text)
    if "outboxes" not in meta:
        raise PortDeclarationError(
            f"{path.name} does not say what its outboxes are.\n"
            "  Add them to the front matter at the top of the file:\n"
            "      ---\n"
            "      emits: ...\n"
            "      outboxes: keep, discard\n"
            "      ---\n"
            "  The framework used to guess by scanning the prose for\n"
            "  'send to <name>', which missed `send to `keep`` and\n"
            "  built a role with no outboxes at all."
        )
    return Ports(
        _name_list(meta.get("inboxes", DEFAULT_INBOX)),
        _name_list(meta["outboxes"]),
        # Absent is meaningful and is not an error: a filter adds no
        # field, it decides. Only a role that claims a field in prose
        # and does not declare it is wrong, and a test asks that
        # question of the prose rather than guessing here.
        _name_list(meta.get("adds", "")),
    )
