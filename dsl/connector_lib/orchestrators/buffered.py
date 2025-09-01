from __future__ import annotations
from typing import Any, Callable, Dict, List
from dsl.core import Agent


class BufferedOrchestrator(Agent):
    """
    Buffers items arriving on 'data_in'. When a control message arrives on
    'command_in', it emits ONE flush command on outport 'out':

        {"cmd": "flush", "payload": [...], "meta": meta(buf)}

    Notes for students:
    - This agent does NOT write to files/Google Sheets/etc. It only sends a
      *flush command*. An OUTPUT CONNECTOR receives that command and performs
      the actual external write.
    - Special message '__STOP__' means: do a final flush (if there is anything
      buffered), then forward '__STOP__' and stop.
    """

    def __init__(
        self,
        meta_builder: Callable[[List[Any]], Dict[str, Any]] | None = None,
        name: str = "BufferedOrchestrator",
    ) -> None:
        # Two input ports, one output port
        super().__init__(name=name, inports=[
            "data_in", "command_in"], outports=["out"])
        self._buf: List[Any] = []
        # meta_builder takes the current buffer and returns a metadata dict
        self._meta_builder = meta_builder or (lambda buf: {})

    def _emit_flush(self) -> None:
        """Build meta, send a single flush command, then clear the buffer."""
        meta = self._meta_builder(self._buf)
        payload = list(self._buf)  # copy for safety
        self.send({"cmd": "flush", "payload": payload,
                  "meta": meta}, outport="out")
        self._buf.clear()

    def run(self) -> None:
        while True:
            msg, inport = self.wait_for_any_port()

            # Global stop handling: final flush (if any), then propagate and exit.
            if msg == "__STOP__":
                if self._buf:
                    self._emit_flush()
                self.send("__STOP__", outport="out")
                return

            if inport == "data_in":
                # Buffer the raw message (often a dict like {"row": ...} or {"data": ...})
                self._buf.append(msg)

            elif inport == "command_in":
                # Emit exactly one flush command (even if buffer is empty — that’s okay)
                self._emit_flush()

            else:
                # Helpful error if ports are miswired
                raise ValueError(f"{self.name}: unknown inport {inport!r}")
