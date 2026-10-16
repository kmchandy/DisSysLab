"""An English role: a prompt sent to a model (spec section 4.2).

The model receives exactly two things:

- as its instructions (the system prompt), the role file's text after the
  front matter, unchanged;
- as the user message, the incoming message as JSON.

Nothing is appended: not the field names, not a format reminder, not
anything about the office. The role's text says what to return, in its
own closing sentence. ``dsl show <role> --prompt`` prints exactly this.

The model is the one named by the agent's ``ai=`` argument in the office
file, or else the default (the ``DSL_BACKEND`` setting, else anthropic).
"""

from __future__ import annotations

import json
from typing import Any

from dissyslab.agents.reply import Message
from dissyslab.agents.role_agent import Call
from dissyslab.backends import get_backend
from dissyslab.office.frontmatter import FrontMatter

#: The longest reply asked of the model, in tokens.
MAX_TOKENS = 2048


def prompt_for(front_matter: FrontMatter) -> str:
    """The system prompt: the role file's text after its front matter."""
    return front_matter.body


def user_message(msg: Message) -> str:
    """The user message: the incoming message as JSON."""
    return json.dumps(msg, ensure_ascii=False)


def english_call(front_matter: FrontMatter, *, ai: str | None = None) -> Call:
    """A ``Call`` that sends the role's prompt and the message to the model."""
    backend = get_backend(ai)
    system = prompt_for(front_matter)

    def call(msg: Message) -> Any:
        return backend.complete(system=system, user=user_message(msg), max_tokens=MAX_TOKENS)

    return call
