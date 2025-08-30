import pathlib
from typing import Any, Dict, List
from .base import OutputConnector


class OutputConnectorFileMarkdown(OutputConnector):
    """Writes a Markdown file on {"cmd":"flush"}.
       - Each payload item becomes a bullet:
         * if dict with 'row' → use that string
         * else → str(item)
    meta: {"path":"...", "title":"Report Title"}  (title optional)
    """

    def __init__(self, default_path: str | None = None, default_title: str = "Report",
                 name: str = "OutputConnectorFileMarkdown") -> None:
        super().__init__(name=name)
        self._cfg = {"title": default_title, **
                     ({"path": default_path} if default_path else {})}

    def _flush(self, payload: List[Any], meta: Dict[str, Any]):
        path = pathlib.Path(meta["path"])
        title = meta.get("title", self._cfg.get("title", "Report"))
        lines = [f"# {title}", ""]
        for p in payload:
            if isinstance(p, dict) and "row" in p:
                lines.append(p["row"])
            else:
                lines.append(f"- {p}")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(lines), encoding="utf-8")
