from __future__ import annotations
from pathlib import Path
from typing import Any, Dict, List
import json
from .base import OutputConnector


class OutputConnectorFileJSON(OutputConnector):
    """
    Write a JSON file on 'flush'.

    Usage (constructor-driven):
        out = OutputConnectorFileJSON(".../data.json")

    Expects a 'flush' command:
        {"cmd": "flush", "payload": [...], "meta": {...}}

    Writes the entire payload list to the path given at construction.
    """

    def __init__(self, path: str, name: str = "OutputConnectorFileJSON") -> None:
        super().__init__(name=name)
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _flush(self, payload: List[Any], meta: Dict[str, Any]) -> None:
        with self.path.open("w", encoding="utf-8") as f:
            json.dump(payload or [], f, indent=2, ensure_ascii=False)
