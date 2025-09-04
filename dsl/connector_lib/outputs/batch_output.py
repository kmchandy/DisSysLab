from __future__ import annotations
from typing import Any, Callable, Dict, List, Optional
from dsl.core import SimpleAgent


class BatchOutput(SimpleAgent):
    """
    Buffer incoming rows (on inport 'in') and emit a single FLUSH command when:
      • buffer size reaches N,
    Also flushes once on '__STOP__'.

    Ports
    -----
    in  : data rows (e.g., {"row": "..."} or any payload you buffer)
    out : {"cmd":"flush", "payload":[...], "meta": meta(buf)}

    Params
    ------
    N : int              flush when buffer reaches N items  (default 50)

    meta_builder : fn(buf) -> dict   builds metadata for the flush (default {})

    Notes
    -----
    - This agent only *emits* a flush command; pair it with an OutputConnector
      (e.g., OutputConnectorFileMarkdown) that performs the actual write.
    """

    def __init__(
        self,
        *,
        N: int = 50,   # default batch size
        meta_builder: Optional[Callable[[List[Any]], Dict[str, Any]]] = None,
        name: str = "BatchOutput",
    ) -> None:
        super().__init__(name=name, inport="in", outports=[
            "out"], handle_msg=self.handle_msg)
        if N <= 0:
            raise ValueError("N must be >= 1")
        self.N = N
        self._buf: List[Any] = []
        self._meta_builder = meta_builder or (lambda buf: {})

    def _emit_flush(self) -> None:
        meta = self._meta_builder(self._buf)
        payload = list(self._buf)  # copy for safety
        self.send({"cmd": "flush", "payload": payload,
                  "meta": meta}, outport="out")
        self._buf.clear()

    def handle_msg(self, msg) -> None:
        if msg == "__STOP__":
            if self._buf:
                self._emit_flush()
            self.send("__STOP__", outport="out")
            return

        self._buf.append(msg)
        if len(self._buf) >= self.N:
            self._emit_flush()
