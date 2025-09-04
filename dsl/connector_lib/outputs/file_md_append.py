from __future__ import annotations
from typing import Dict, Any, List
import pathlib
from .base import OutputConnector


class OutputConnectorFileMarkdownAppend(OutputConnector):
    """
    Append-mode Markdown writer.

    Expects a flush command message upstream to look like:
      {"cmd": "flush", "payload": [<rows>], "meta": {"title": "..."}}

    - Appends rows to the file on every flush.
    - Writes a "# Title" header only if the file is empty / doesn't exist.
    - Each item in payload may be:
        * a string (already a Markdown line), or
        * a dict with key 'row' (common in our examples).
    """

    def __init__(self, path: str, title: str = "Report", name: str = "OutputConnectorFileMarkdownAppend"):
        super().__init__(name=name)
        self.path = pathlib.Path(path)
        self.title = title
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _flush(self, payload: List[Dict[str, Any]], meta: Dict[str, Any]):
        # Write header once (first time only)
        write_header = (not self.path.exists()) or (
            self.path.stat().st_size == 0)
        lines: List[str] = []
        if write_header:
            lines.append(f"# {meta.get('title', self.title)}")
            lines.append("")  # blank line after header

        for p in payload:
            if isinstance(p, str):
                lines.append(p)
            else:
                lines.append(p.get("row", str(p)))

        with self.path.open("a", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
