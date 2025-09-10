# dsl/block_lib/sinks/sink.py
from __future__ import annotations

from typing import Callable, Any, Optional
import traceback
from dsl.core import SimpleAgent, STOP

# Style B: record functions accept ONLY the message
RecordFn = Callable[[Any], None]


class Sink(SimpleAgent):
    """
    Terminal agent that consumes messages.
    Calls `record_fn(msg)` for every non-STOP message.
    STOP messages are consumed and not recorded.
    """

    def __init__(self, name: str = "Sink", record_fn: Optional[RecordFn] = None):
        if record_fn is None:
            raise ValueError("record_fn is required for Sink")
        self.record_fn: RecordFn = record_fn

        # SimpleAgent will call this with ONE argument: the message.
        def _handle_msg(msg: Any) -> None:
            # Consume STOP silently
            if msg is STOP:
                return
            try:
                self.record_fn(msg)
            except Exception:
                # Don't crash the agent loop if user callback raises
                with open("dsl_debug.log", "a") as log:
                    log.write(f"\n--- {self.__class__.__name__} Error ---\n")
                    log.write(traceback.format_exc())

        super().__init__(name=name, inport="in", outports=[], handle_msg=_handle_msg)
