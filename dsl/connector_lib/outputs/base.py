from __future__ import annotations
from typing import Any, Dict, List
from dsl.core import SimpleAgent


class OutputConnector(SimpleAgent):
    """
    Base class for flush-style outputs with optional streaming.

    Ports:
      - in ('in'): commands
      - append_in (optional): per-item values (Any) to buffer
      - status, error

    Commands:
      - {"cmd":"flush","payload":[...], "meta":{...}}   # payload optional; uses buffer
      - {"cmd":"configure","meta":{...}}                # optional

    On success: {"event":"flushed","count":N}
    """

    def __init__(self, name: str = "OutputConnector") -> None:
        super().__init__(name=name, inport="in", outports=["status", "error"])
        self.inports = ["in", "append_in"]
        self._buf: List[Any] = []
        self._cfg: Dict[str, Any] = {}

    def process(self, msg, inport=None):
        try:
            if inport == "append_in":
                self._buf.append(msg)
                return

            cmd = (msg or {}).get("cmd")
            if cmd == "configure":
                meta = (msg or {}).get("meta", {}) or {}
                self._cfg.update(meta)
                self.send({"event": "configured"}, outport="status")
                return

            if cmd == "flush":
                payload = (msg or {}).get("payload")
                meta = {**self._cfg, **((msg or {}).get("meta", {}) or {})}
                # normalize items to a list[Any]
                if payload is None:
                    items: List[Any] = list(self._buf)
                elif isinstance(payload, list):
                    items = payload
                else:
                    items = [payload]

                self._flush(items, meta)
                self._buf.clear()
                self.send({"event": "flushed", "count": len(items)},
                          outport="status")
                return

            self.send(
                {"event": "error", "message": f"unknown cmd {cmd}"}, outport="error")
        except Exception as e:
            self.send({"event": "error", "cmd": (msg or {}).get(
                "cmd", "?"), "message": repr(e)}, outport="error")

    def _flush(self, payload: List[Any], meta: Dict[str, Any]):
        raise NotImplementedError
