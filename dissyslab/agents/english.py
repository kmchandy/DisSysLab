"""An English role: a prompt sent to a model (spec section 4.2).

The model receives exactly two things:

- as its instructions (the system prompt), the role file's text after the
  front matter, unchanged;
- as the user message, the incoming message as JSON.

Nothing is appended: not the field names, not a format reminder, not
anything about the office. The role's text says what to return, in its
own closing sentence. ``dsl show <role> --prompt`` prints exactly this.

One thing goes alongside, not into, the prompt. When every field of the
role's ``out:`` says what it holds (values, ``number``, ``integer`` or
``text``) and the model's backend can enforce a schema (Anthropic's
structured outputs), the reply's shape is sent as a JSON schema, and the
API constrains the model to it. A model that knows the right shape still
slips now and then -- Haiku 5.5 once answered in plain text, which the
contract refused, and the refusal stopped Lab 1 at the eighth customer --
and a slip in the shape is not what a contract is there to catch. The
API adds its own short instruction about the format; DisSysLab adds
nothing. Ranges and lengths are not sent (the API does not support
them); the contract still checks them, as it checks everything else.

A role with a field that may hold anything (``out: entities``) gets no
schema, because a schema cannot say "anything": it runs as before.

The model is the one named by the agent's ``ai=`` argument in the office
file, or else the default (the ``DSL_BACKEND`` setting, else anthropic).
"""

from __future__ import annotations

import json
from typing import Any

from dissyslab.agents.reply import Message
from dissyslab.agents.role_agent import Call
from dissyslab.backends import get_backend
from dissyslab.office.frontmatter import Field, FrontMatter

#: The longest reply asked of the model, in tokens.
MAX_TOKENS = 2048

_TYPES = {"number": "number", "integer": "integer", "text": "string"}


def _looks_numeric(value: str) -> bool:
    try:
        float(value)
    except ValueError:
        return False
    return True


def prompt_for(front_matter: FrontMatter) -> str:
    """The system prompt: the role file's text after its front matter."""
    return front_matter.body


def user_message(msg: Message) -> str:
    """The user message: the incoming message as JSON."""
    return json.dumps(msg, ensure_ascii=False)


def _field_schema(field: Field) -> dict[str, Any] | None:
    if field.values:
        # Named values are words (yes | no). Values that look like numbers
        # (1 | 2 | 3) could arrive as either, so they get no schema.
        if any(_looks_numeric(v) for v in field.values):
            return None
        return {"type": "string", "enum": list(field.values)}
    if field.type in _TYPES:
        return {"type": _TYPES[field.type]}
    return None


def reply_schema(front_matter: FrontMatter) -> dict[str, Any] | None:
    """The JSON schema of the reply ``out:`` asks for, or None if it cannot
    be written exactly: no ``out:``, ``out: same as in``, ``out if`` lines,
    or a field that may hold anything."""
    fields = front_matter.outputs
    if not fields or front_matter.same_as_in or front_matter.conditionals:
        return None
    properties: dict[str, Any] = {}
    for field in fields:
        schema = _field_schema(field)
        if schema is None:
            return None
        properties[field.name] = schema
    return {"type": "object", "properties": properties,
            "required": [f.name for f in fields], "additionalProperties": False}


def english_call(front_matter: FrontMatter, *, ai: str | None = None) -> Call:
    """A ``Call`` that sends the role's prompt and the message to the model."""
    backend = get_backend(ai)
    system = prompt_for(front_matter)
    schema = reply_schema(front_matter) if getattr(backend, "supports_schema", False) else None

    def call(msg: Message) -> Any:
        if schema is not None:
            return backend.complete(system=system, user=user_message(msg),
                                    max_tokens=MAX_TOKENS, schema=schema)
        return backend.complete(system=system, user=user_message(msg), max_tokens=MAX_TOKENS)

    return call
