from __future__ import annotations
from typing import Any, Callable, Dict, List, Optional
import time
from dsl.core import Agent


class Orchestrator(Agent):
    """
    Buffer rows and emit a single FLUSH command when:
      • buffer size reaches N, OR
      • time since last flush >= T seconds (and buffer isn't empty), OR
      • a message arrives on 'command_in' (manual/explicit flush trigger).
    Also flushes on '__STOP__'.

    Ports
    -----
    in          : data rows (e.g., {"row": "..."} or any payload you buffer)
    command_in  : any message triggers an immediate flush (if buffer non-empty)
    out         : {"cmd":"flush", "payload":[...], "meta": meta(buf)}

    Params
    ------
    N : int              flush when buffer reaches N items  (default 50)
    T : float            also flush every T seconds if buffer non-empty (default 2.0)
    meta_builder : fn(buf) -> dict   builds metadata for the flush (default {})
    """

    def __init__(
        self,
        *,
        N: int = 50,
        T: float = 2.0,
        meta_builder: Optional[Callable[[List[Any]], Dict[str, Any]]] = None,
        name: str = "Orchestrator",
    ) -> None:
        super().__init__(
            name=name, inports=["in", "command_in"], outports=["out"], run=self.run
        )
        if N <= 0:
            raise ValueError("N must be >= 1")
        if T <= 0:
            raise ValueError("T must be > 0")

        self.N = N
        self.T = T
        self._buf: List[Any] = []
        self._meta_builder = meta_builder or (lambda buf: {})
        self._last_flush_at = time.monotonic()

    def _emit_flush(self) -> None:
        meta = self._meta_builder(self._buf)
        payload = list(self._buf)
        self.send({"cmd": "flush", "payload": payload,
                  "meta": meta}, outport="out")
        self._buf.clear()
        self._last_flush_at = time.monotonic()

    def run(self) -> None:
        SLEEP = 0.01
        while True:
            # Prefer command_in (explicit flush) when available
            cmd = self.recv_if_waiting_msg("command_in")
            if cmd is not None:
                if cmd == "__STOP__":
                    if self._buf:
                        self._emit_flush()
                    self.send("__STOP__", outport="out")
                    return
                if self._buf:
                    self._emit_flush()
                time.sleep(SLEEP)
                continue

            msg = self.recv_if_waiting_msg("in")
            if msg is not None:
                if msg == "__STOP__":
                    if self._buf:
                        self._emit_flush()
                    self.send("__STOP__", outport="out")
                    return
                self._buf.append(msg)
                if len(self._buf) >= self.N:
                    self._emit_flush()
            else:
                if self._buf and (time.monotonic() - self._last_flush_at) >= self.T:
                    self._emit_flush()

            time.sleep(SLEEP)
