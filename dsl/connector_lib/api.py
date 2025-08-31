from __future__ import annotations
from typing import Any, Callable, Dict, Iterable, List, Optional
from dsl.core import SimpleAgent

ReadFn = Callable[..., Any]   # returns value or Iterable[value]
WriteFn = Callable[..., Any]   # accepts value(s)


def input_from(read_fn: ReadFn, name: str = "InputFrom"):
    """
    Wrap a plain Python function into a pull-style input connector block.

    in ('in'):  {"cmd":"pull","args":{...}}
    out:        {"data": value}  (one per item; iterable results expanded)
    status:     {"event":"done","cmd":"pull","count":N}
    error:      {"event":"error","cmd":"pull","message":"..."}
    """
    class _Input(SimpleAgent):
        def __init__(self):
            super().__init__(name=name, inport="in",
                             outports=["out", "status", "error"])

        def process(self, msg: Dict[str, Any], inport=None):
            try:
                if (msg or {}).get("cmd", "pull") != "pull":
                    self.send(
                        {"event": "error", "message": "unknown cmd"}, outport="error")
                    return
                args = (msg or {}).get("args", {}) or {}
                res = read_fn(**args)
                count = 0
                if isinstance(res, Iterable) and not isinstance(res, (str, bytes, dict)):
                    for it in res:
                        self.send({"data": it}, outport="out")
                        count += 1
                else:
                    self.send({"data": res}, outport="out")
                    count = 1
                self.send({"event": "done", "cmd": "pull",
                          "count": count}, outport="status")
            except Exception as e:
                self.send({"event": "error", "cmd": "pull",
                          "message": repr(e)}, outport="error")
    return _Input()


def output_to(write_fn: WriteFn, *, default_meta: Optional[Dict[str, Any]] = None,
              name: str = "OutputTo", enable_streaming: bool = True):
    """
    Wrap a plain Python function into a flush-style output connector block.

    - append_in (optional): per-item values (Any) are buffered
    - in ('in'):
        {"cmd":"flush","payload":[...], "meta":{...}}  # payload optional; uses buffer if missing
        {"cmd":"configure","meta":{...}}               # persist meta defaults
    status: {"event":"flushed","count":N} | {"event":"configured"}
    error:  {"event":"error","cmd":..., "message":"..."}
    """
    class _Output(SimpleAgent):
        def __init__(self):
            super().__init__(name=name, inport="in",
                             outports=["status", "error"])
            self.inports = ["in", "append_in"] if enable_streaming else ["in"]
            self._buf: List[Any] = []
            self._meta: Dict[str, Any] = dict(default_meta or {})

        def process(self, msg, inport=None):
            try:
                if inport == "append_in":
                    self._buf.append(msg)
                    return

                cmd = (msg or {}).get("cmd")
                if cmd == "configure":
                    self._meta.update((msg or {}).get("meta", {}) or {})
                    self.send({"event": "configured"}, outport="status")
                    return

                if cmd == "flush":
                    meta = {**self._meta, **
                            ((msg or {}).get("meta", {}) or {})}
                    payload = (msg or {}).get("payload", None)
                    # normalize items (Any): list from payload or from buffer
                    if payload is None:
                        items: List[Any] = list(self._buf)
                    elif isinstance(payload, Iterable) and not isinstance(payload, (str, bytes, dict)):
                        items = list(payload)
                    else:
                        items = [payload]

                    # Try bulk call; if write_fn signature expects single item, fall back
                    try:
                        write_fn(items, **meta)   # bulk attempt
                        count = len(items)
                    except TypeError:
                        count = 0
                        for v in items:
                            write_fn(v, **meta)
                            count += 1

                    self._buf.clear()
                    self.send({"event": "flushed", "count": count},
                              outport="status")
                    return

                self.send(
                    {"event": "error", "message": f"unknown cmd {cmd}"}, outport="error")
            except Exception as e:
                self.send({"event": "error", "cmd": (msg or {}).get(
                    "cmd", "?"), "message": repr(e)}, outport="error")
    return _Output()
