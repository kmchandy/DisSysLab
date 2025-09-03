from __future__ import annotations
from pathlib import Path
from typing import Any, Dict, List
from .base import OutputConnector


class OutputConnectorFileMarkdown(OutputConnector):
    """
    Write a Markdown report on 'flush'.

    Usage (constructor-driven):
        out = OutputConnectorFileMarkdown(".../report.md", title="Issue Triage")

    Expects a 'flush' command:
        {"cmd": "flush", "payload": [rows], "meta": {...}}

    Each payload item can be:
      - a string (written as-is)
      - a dict with key 'row' (string)
      - anything else (stringified)
    """

    def __init__(self, path: str, title: str = "Report",
                 name: str = "OutputConnectorFileMarkdown") -> None:
        super().__init__(name=name)
        self.path = Path(path)
        self.title = title
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _flush(self, payload: List[Any], meta: Dict[str, Any]) -> None:
        lines = [f"# {self.title}", ""]
        for item in (payload or []):
            if isinstance(item, str):
                lines.append(item)
            elif isinstance(item, dict) and "row" in item:
                lines.append(str(item["row"]))
            else:
                lines.append(str(item))
        self.path.write_text("\n".join(lines), encoding="utf-8")
