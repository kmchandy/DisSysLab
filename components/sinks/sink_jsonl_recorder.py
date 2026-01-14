# dsl/connectors/sink_jsonl_recorder.py

from __future__ import annotations
import json
from typing import Any, Dict, Optional


class JSONLRecorder:
    """
    JSON Lines: write each message dict as one JSON object per line.
    """

    def __init__(
        self,
        path: str = "anomaly_stream.jsonl",
        *,
        name: Optional[str] = None,
        mode: str = "w",          # "w" overwrite, "a" append
        flush_every: int = 1,     # flush after N records
        ensure_ascii: bool = False,
        sort_keys: bool = False,
    ):
        self.path = path
        self.mode = mode
        self.flush_every = max(1, int(flush_every))
        self.ensure_ascii = ensure_ascii
        self.sort_keys = sort_keys

        self._fh = open(self.path, self.mode, encoding="utf-8")
        self._name = name or "jsonl_recorder"
        self._count = 0

    @property
    def __name__(self) -> str:
        return self._name

    def __call__(self, msg: Dict[str, Any]):
        print(f"in JSLONLRecorder: msg = {msg}")
        self._fh.write(
            json.dumps(msg, default=str, ensure_ascii=self.ensure_ascii,
                       sort_keys=self.sort_keys)
            + "\n"
        )
        self._count += 1
        if self._count % self.flush_every == 0:
            try:
                self._fh.flush()
            except Exception:
                pass
        return msg

    def finalize(self):
        try:
            self._fh.flush()
            self._fh.close()
        except Exception:
            pass

    run = __call__
