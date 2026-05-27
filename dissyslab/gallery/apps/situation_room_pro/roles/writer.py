"""Local override of the framework's ``writer`` role: use Claude.

This file is the ONLY thing that distinguishes ``situation_room_pro``
from ``situation_room``. Everything else — sources, sinks, the four
extractors (entity, severity, topic, location), Sync, Riley, Jordan,
and the wiring — is identical. The framework's local-roles search
sees this file and uses it instead of the framework-shipped
``dissyslab/roles/writer.md`` whose backend defaults to whatever
``DSL_BACKEND`` says.

The pattern
===========

Per-role backend override: read the framework's prompt text once,
re-wrap with ``nl_role(prompt, AI="claude")``. The override is
inert at import time (no API call); Claude is only consulted when
Riley processes a message at run time.

Why a "pro" variant
===================

The cost/quality story Pat-Builder should care about, summarised:

* Free SLM (Qwen3:30b via Ollama) does the four extractors cheaply
  and reliably — these are closed-list classifications and named-
  entity extraction where the role-decomposition pattern keeps
  output structured.
* Generation-heavy roles (the writer producing a 2-4-sentence
  briefing, the evaluator deciding publish-vs-revise) benefit more
  from a stronger model. The quality lift on Pat's morning digest
  is visible.
* Mixing one role on Claude and the rest on Qwen costs pennies per
  day on a Pat-volume office, vs ~$14/month for the whole office
  on Claude. Riley typically uses ~300-500 tokens per article;
  at Sonnet 4.5 pricing that's well under $0.05 per typical
  morning run.

The same pattern works for any role in any office: drop a ``.py``
override in the office's ``roles/`` folder, point it at the
framework's prompt, set the backend you want.
"""
from pathlib import Path

import dissyslab
from dissyslab.office import nl_role


# Locate the framework's writer prompt without duplicating its text.
# The override is purely about backend selection.
_FRAMEWORK_WRITER = (
    Path(dissyslab.__file__).resolve().parent / "roles" / "writer.md"
)

role = nl_role(
    _FRAMEWORK_WRITER.read_text(),
    AI="claude",
)
