# dsl/blocks/sink.py
from __future__ import annotations

from typing import Callable, Any, Optional, Dict
import traceback
from dsl.core import Agent, STOP
from dsl.utils import filter_kwargs


class Sink(Agent):
    """
    Terminal agent that consumes messages.
    Calls `fn(msg, **params)` for every non-STOP, non-None message.
    STOP is consumed (not recorded).
    """

    def __init__(self, *, fn: Optional[Callable[..., Any]] = None, params: Optional[Dict[str, Any]] = None) -> None:
        if not callable(fn):
            raise TypeError(
                "Sink(fn=...) must be callable (fn(msg, **params)).")
        super().__init__(inports=["in"], outports=[])
        self._fn = fn
        # Ignore stray keys in params; only pass what fn accepts
        self._params: Dict[str, Any] = filter_kwargs(fn, params or {})

    def run(self) -> None:
        try:
            while True:
                msg = self.recv("in")
                # STOP: swallow and close input
                if isinstance(msg, str) and msg == STOP:
                    try:
                        self.close("in")
                    finally:
                        return
                # None=drop (do not record)
                if msg is None:
                    continue
                try:
                    self._fn(msg, **self._params)
                except Exception as e:
                    print(f"[Sink] Error in fn: {e}")
                    print(traceback.format_exc())
                    return
        except Exception as e:
            print(f"[Sink] Error: {e}")
            print(traceback.format_exc())
            return
