from __future__ import annotations
from typing import Any, Callable, Dict, List
from dsl.core import SimpleAgent


class BufferedOrchestrator(SimpleAgent):
    """
    Buffers rows on 'data_in'; on 'tick_in', emits one flush command:
      {"cmd":"flush","payload":[...], "meta": meta(buf)}
    """

    def __init__(self, meta_builder: Callable[[List[Any]], Dict[str, Any]] | None = None,
                 name: str = "BufferedOrchestrator") -> None:
        super().__init__(name=name, inport=None, outports=["out"])
        self.inports = ["data_in", "tick_in"]
        self._buf: List[Any] = []
        self._meta_builder = meta_builder or (lambda buf: {})

    def process(self, msg, inport=None):
        if inport == "data_in":
            self._buf.append(msg)
        elif inport == "tick_in":
            meta = self._meta_builder(self._buf)
            self.send({"cmd": "flush", "payload": list(
                self._buf), "meta": meta}, outport="out")
            self._buf = []
