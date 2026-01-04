# dsl/connectors/sink_jsonl_recorder.py

from __future__ import annotations
import json
from typing import Dict, Optional


class JSONLRecorder:
    """
    JSON Lines: Append selected fields to a JSONL file (one record per message).
    """

    def __init__(self, path: str = "anomaly_stream.jsonl", *, name: Optional[str] = None):
        self.path = path
        self._fh = open(self.path, "w", encoding="utf-8")  # file handle
        self._name = name or "jsonl_recorder"

    @property
    def __name__(self) -> str:
        return self._name

    def __call__(self, msg: Dict[str, float]):
        self._fh.write(json.dumps(msg, default=str) + "\n")
        return msg

    def finalize(self):
        try:
            self._fh.flush()
            self._fh.close()
        except Exception:
            pass

    run = __call__
