# dsl/block_lib/sinks/sink.py
from __future__ import annotations

from typing import Callable, Any, Optional, Dict
import traceback
from dsl.core import SimpleAgent, STOP, filtered_kwargs


class Sink(SimpleAgent):
    """
    Terminal agent that consumes messages.
    Calls `record_fn(msg)` for every non-STOP message.
    STOP messages are consumed and not recorded.
    """

    def __init__(
        self,
        *,
        name: str = "Sink",
        record_fn: Optional[Callable[..., None]] = None,
        kwargs: Optional[Dict[str, Any]] = None,
    ) -> None:
        if record_fn is None:
            raise ValueError("record_fn is required for Sink")
        super().__init__(
            name=name,
            inport="in",
            outports=[],
        )
        self.record_fn = record_fn
        self.kwargs = kwargs or {}

    def handle_msg(self, msg: Any) -> None:
        if msg == STOP:
            return
        try:
            self.record_fn(msg, **self.kwargs)
        except Exception:
            raise RuntimeError(
                f"Sink {self.name} record_fn raised:\n{traceback.format_exc()}"
            ) from None
