# dsl/blocks/transform.py
from __future__ import annotations
from typing import Any, Callable, Optional, Dict
import traceback

from dsl.core import Agent, STOP


class Transform(Agent):
    """
    Inports: ["in"], Outports: ["out"].

    Contract (one way only):
      - fn: callable of shape fn(msg, **kwargs) -> Any

    Behavior:
      - Forwards STOP and terminates.
      - On exception: prints traceback and emits STOP.
    """

    def __init__(self, *, fn: Callable[..., Any], params: Optional[Dict[str, Any]] = None):
        if not callable(fn):
            raise TypeError(
                "Transform(fn=...) must be callable (fn(msg, **params)).")
        self._fn = fn
        self._kwargs: Dict[str, Any] = dict(params) if params else {}

        super().__init__(inports=["in"], outports=["out"])

    def run(self) -> None:
        try:
            while True:
                msg = self.recv("in")

                if msg is STOP:
                    self.send(STOP, "out")
                    return
                try:
                    result = self._fn(msg, **self._kwargs)
                except Exception as e:
                    print(f"[Transform] Error in fn: {e}")
                    print(traceback.format_exc())
                    self.send(STOP, "out")
                    return
                self.send(result, "out")
        except Exception as e:
            print(f"[Transform] Error: {e}")
            print(traceback.format_exc())
            self.send(STOP, "out")

    def __repr__(self) -> str:
        fn_name = getattr(self._fn, "__name__", repr(self._fn))
        return f"<Transform fn={fn_name}>"

    def __str__(self) -> str:
        return "Transform"
