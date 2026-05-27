# dissyslab/components/sinks/message_coerce.py
"""Normalize heterogeneous agent output into dict messages for sinks."""

from __future__ import annotations

import re
from typing import Any, Mapping

# Unicode bullet (U+2022), common in matcher / briefing prompts.
_BULLET = "\u2022"
_BULLET_SEP = f" {_BULLET} "


def normalize_multibullet_lines(text: str) -> str:
    """Break ``• A … • B …`` clumped on one line so each ``•`` starts a new line.

    Models often emit ``• Title: … • Company: …`` as a single paragraph; email
    and Markdown read more clearly with one field per line.
    """
    if not text or _BULLET_SEP not in text:
        return text
    out: list[str] = []
    for line in text.splitlines():
        if _BULLET_SEP in line and line.count(_BULLET) >= 2:
            out.append(line.replace(_BULLET_SEP, f"\n{_BULLET} "))
        else:
            out.append(line)
    joined = "\n".join(out)
    return re.sub(r"\n{3,}", "\n\n", joined)


def coerce_sink_message(msg: Any) -> dict[str, Any]:
    """Return a dict with at least ``text`` (and fields sinks commonly read).

    LLM-driven agents sometimes emit a bare string instead of JSON; sinks such as
    ``IntelligenceDisplay`` and ``GmailSink`` expect ``.get``-able mappings.
    """
    if isinstance(msg, Mapping):
        return dict(msg)
    if isinstance(msg, str):
        s = msg.strip()
        title = (s[:72] + "…") if len(s) > 72 else s
        return {
            "text": s,
            "title": title or "(empty)",
            "significance": "MEDIUM",
            "source": "agent",
        }
    return {
        "text": str(msg),
        "title": str(msg)[:72],
        "significance": "MEDIUM",
        "source": "agent",
    }
