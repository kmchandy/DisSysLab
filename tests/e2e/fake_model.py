"""A scripted stand-in for every language model, for end-to-end tests.

``dsl run`` imports the module named in ``DSL_BACKEND_MODULE`` before it
runs anything (cli.main). Importing this module replaces every registered
backend (anthropic, openai, openrouter, ollama, gemini, and their
variants) with ``ScriptedModel``, so an office runs with no network and
no API key, and gives the same replies every time.

The script is a JSON file named by ``DSL_FAKE_SCRIPT``: a list of rules,
tried in order. The first rule whose ``"when"`` text occurs in the
role's prompt (the system prompt) gives the reply::

    [
      {"when": "You are an agent named **Qwen**",
       "reply": "{\\"qwen\\": {\\"answer\\": \\"247\\", ...}}"},
      {"when": "You are Riley",
       "reply": "{\\"send_to\\": \\"finish\\", \\"problem_id\\": \\"$problem_id\\"}"}
    ]

A rule may also give ``"user_contains"``, a string or a list of strings:
then it applies only when each occurs in the incoming message as well,
which lets one role answer differently for different messages.

``$name`` in a reply is replaced by that field of the incoming message
(the user prompt is the message as JSON), so a reply can copy fields
through. A prompt that matches no rule is a test error: the model's
reply would otherwise be invented, and the test would pass for the wrong
reason.

Every call is appended to the file named by ``DSL_FAKE_LOG``, if set, as
one JSON line ``{"when": ..., "user": ...}``, so a test can check which
roles were consulted and with what.
"""

from __future__ import annotations

import json
import os
import string
import threading
from typing import Any

from dissyslab.backends import _ALIASES, _REGISTRY, register_backend

_LOG_LOCK = threading.Lock()


class ScriptedModel:
    """Answers from the rules in ``DSL_FAKE_SCRIPT``."""

    def __init__(self) -> None:
        path = os.environ.get("DSL_FAKE_SCRIPT")
        if not path:
            raise RuntimeError("DSL_FAKE_SCRIPT is not set")
        with open(path, encoding="utf-8") as f:
            self.rules: list[dict[str, Any]] = json.load(f)
        self.log = os.environ.get("DSL_FAKE_LOG")

    def complete(
        self,
        *,
        system: str,
        user: str,
        max_tokens: int = 1024,
        temperature: float = 1.0,
        model: str | None = None,
    ) -> str:
        for rule in self.rules:
            wanted = rule.get("user_contains", [])
            if isinstance(wanted, str):
                wanted = [wanted]
            if rule["when"] in system and all(w in user for w in wanted):
                try:
                    fields = json.loads(user)
                except ValueError:
                    fields = {}
                values = {k: v for k, v in fields.items() if isinstance(v, (str, int, float))}
                reply = string.Template(rule["reply"]).safe_substitute(values)
                if self.log:
                    # Agents call from several threads at once. On Windows
                    # an append is a seek then a write, not one step, so
                    # unlocked writers overwrote each other's lines.
                    with _LOG_LOCK, open(self.log, "a", encoding="utf-8") as f:
                        f.write(json.dumps({"when": rule["when"], "user": user}) + "\n")
                return reply
        raise RuntimeError(
            "fake model: no rule matches this prompt; its first line is "
            f"{system.strip().splitlines()[0]!r}"
        )


_MODEL: ScriptedModel | None = None


def _shared() -> ScriptedModel:
    global _MODEL
    if _MODEL is None:
        _MODEL = ScriptedModel()
    return _MODEL


for _name in list(_REGISTRY) + list(_ALIASES):
    register_backend(_name, _shared)
