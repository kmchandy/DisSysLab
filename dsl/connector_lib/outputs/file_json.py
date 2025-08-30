import json
import pathlib
from typing import Any, Dict, List
from .base import OutputConnector


class OutputConnectorFileJSON(OutputConnector):
    """Writes a JSON file on {"cmd":"flush"}; accepts payload of Any or list[Any].
       If given dicts/strings/numbers, writes a JSON array.
    meta: {"path": "..."}
    """

    def __init__(self, default_path: str | None = None,
                 name: str = "OutputConnectorFileJSON") -> None:
        super().__init__(name=name)
        if default_path:
            self._cfg = {"path": default_path}

    def _flush(self, payload: List[Any], meta: Dict[str, Any]):
        path = pathlib.Path(meta["path"])
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
