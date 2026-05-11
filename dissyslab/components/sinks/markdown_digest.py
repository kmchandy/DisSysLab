# dissyslab/components/sinks/markdown_digest.py

"""
MarkdownDigest sink — write the day's briefings as a single readable
markdown file.

Use case: Pat-B (situation-room scanner) wants to open *one* file at
8am with her morning intelligence digest, not watch a terminal stream.
``MarkdownDigest`` accumulates briefings as they arrive and appends
each one as a section to a file on disk. The file is always usable —
mid-run, after-run, anytime.

Output shape per briefing
=========================

```markdown
## [SEVERITY] Headline  *(✓ publish | ⚠ revise)*

*topic · country · region*

A 2-4 sentence summary written by the writer role.

> Editor's note (when Jordan flagged for revision):
> Jordan's feedback string.

[source](url)
```

The severity badge and verdict marker make scanning easy. Pat reads
the headlines first; drills into summaries selectively.

Usage in office.md
==================

::

    Sinks: markdown_digest(path="~/morning_digest.md"), discard
    ...
    Jordan's publish is markdown_digest.
    Jordan's revise is markdown_digest.

Both `publish` and `revise` routes can target the same digest file;
the verdict marker visually distinguishes them.
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional


# Glyphs used in the rendered digest. These render as plain ASCII
# everywhere; emoji could be used instead but ASCII keeps the file
# diff-friendly and email-safe.
_VERDICT_GLYPHS = {
    "publish": "✓ publish",
    "revise": "⚠ revise",
}


class MarkdownDigest:
    """Sink that appends each briefing as a markdown section.

    Parameters
    ----------
    path
        Where to write the digest file. ``~`` expands to the user's
        home directory; parent directories are created if missing.
        Default: ``./morning_digest.md`` in the current working
        directory.
    mode
        ``"w"`` (overwrite — default) or ``"a"`` (append). Use ``"a"``
        for continuous-run offices that want to accumulate across
        polls; use ``"w"`` for one-shot runs that want a fresh file
        each morning.
    title
        Header text at the top of the file. Default includes today's
        date so the digest is self-dated.
    """

    def __init__(
        self,
        path: str = "morning_digest.md",
        *,
        name: Optional[str] = None,
        mode: str = "w",
        title: Optional[str] = None,
    ):
        self.path = Path(os.path.expanduser(path)).resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)

        if title is None:
            title = f"Morning digest — {datetime.now().strftime('%Y-%m-%d')}"

        # Open once; append per message. ``buffering=1`` gives
        # line-buffered writes so Pat can `tail -f` the file mid-run.
        self._fh = open(self.path, mode, encoding="utf-8", buffering=1)
        self._name = name or "markdown_digest"
        self._count = 0

        if mode == "w":
            self._fh.write(f"# {title}\n\n")
            self._fh.flush()

    @property
    def __name__(self) -> str:
        return self._name

    def __call__(self, msg: Any) -> Any:
        """Append one briefing as a markdown section."""
        if not isinstance(msg, dict):
            # Non-dict input — render as a code block so nothing is
            # silently dropped.
            self._fh.write("```\n")
            self._fh.write(str(msg))
            self._fh.write("\n```\n\n---\n\n")
            return msg

        self._fh.write(self._render(msg))
        self._fh.write("\n---\n\n")
        self._count += 1
        return msg

    def _render(self, msg: Dict[str, Any]) -> str:
        """Render one briefing as a markdown section."""
        severity = msg.get("severity", "")
        headline = msg.get("headline") or msg.get("title") or "(no headline)"
        verdict = msg.get("verdict")
        feedback = msg.get("feedback")
        summary = msg.get("summary") or msg.get("text", "")
        url = msg.get("url", "")
        source = msg.get("source", "")
        topic = msg.get("topic", "")
        location = msg.get("location") or {}
        country = location.get("country", "") if isinstance(location, dict) else ""
        region = location.get("region", "") if isinstance(location, dict) else ""

        lines: list[str] = []

        # Header: ## [SEVERITY] Headline (verdict)
        sev_badge = f"[{severity}] " if severity else ""
        verdict_suffix = ""
        if verdict in _VERDICT_GLYPHS:
            verdict_suffix = f"  *({_VERDICT_GLYPHS[verdict]})*"
        lines.append(f"## {sev_badge}{headline}{verdict_suffix}")
        lines.append("")

        # Metadata line: *topic · country · region*
        meta_parts = [p for p in (topic, country, region) if p]
        if meta_parts:
            lines.append(f"*{' · '.join(meta_parts)}*")
            lines.append("")

        # Summary body
        if summary:
            lines.append(summary)
            lines.append("")

        # Editor's note when flagged for revision
        if verdict == "revise" and feedback:
            lines.append(f"> *Editor's note:* {feedback}")
            lines.append("")

        # Source link
        if url:
            label = source if source else "source"
            lines.append(f"[{label}]({url})")
            lines.append("")

        return "\n".join(lines)

    def finalize(self) -> None:
        """Flush and close the file. Idempotent."""
        try:
            self._fh.flush()
            self._fh.close()
        except Exception:
            pass

    # The framework's Sink wrapper calls .run(msg) on each message;
    # ``run`` is the canonical entrypoint.
    run = __call__
