from __future__ import annotations
from typing import Any, Dict, Iterable
from dsl.core import SimpleAgent


class InputConnector(SimpleAgent):
    """
    Base class for pull-style inputs.

    in ('in'):  {"cmd":"pull","args":{...}}
    out:        {"data": <item>} per item
    status:     {"event":"done","cmd":"pull","count":N}
    error:      {"event":"error","cmd":"pull","message":"..."}
    """

    def __init__(self, name: str = "InputConnector") -> None:
        super().__init__(name=name, inport="in",
                         outports=["out", "status", "error"])

    def process(self, msg: Dict[str, Any], inport=None):
        cmd = (msg or {}).get("cmd", "pull")
        args = (msg or {}).get("args", {}) or {}
        if cmd != "pull":
            self.send(
                {"event": "error", "message": f"unknown cmd {cmd}"}, outport="error")
            return
        try:
            count = 0
            for item in self._pull(cmd, args):
                self.send({"data": item}, outport="out")
                count += 1
            self.send({"event": "done", "cmd": cmd,
                      "count": count}, outport="status")
        except Exception as e:
            self.send({"event": "error", "cmd": cmd,
                      "message": repr(e)}, outport="error")

    def _pull(self, cmd: str, args: Dict[str, Any]) -> Iterable[Any]:
        raise NotImplementedError
