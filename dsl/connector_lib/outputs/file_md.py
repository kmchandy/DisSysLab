# dsl/connector_lib/outputs/file_md.py
from __future__ import annotations
from typing import Any, Dict, List
from .base import OutputConnector


class OutputConnectorFileMarkdown(OutputConnector):
    """Write a Markdown file on {"cmd":"flush","payload":[...],"meta":{"path":"...", "title":"..."}}."""

    def _flush(self, payload: List[Any], meta: Dict[str, Any]) -> None:
        import pathlib
        path = pathlib.Path(meta["path"])
        title = meta.get("title", "Report")

        lines = [f"# {title}", ""]
        for item in payload:
            if isinstance(item, dict) and "row" in item:
                lines.append(item["row"])
            else:
                lines.append(f"- {item}")

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(lines), encoding="utf-8")
