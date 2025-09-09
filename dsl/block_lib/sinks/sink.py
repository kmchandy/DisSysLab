"""
Sink: a SimpleAgent that receives messages and records them
via a user-provided function `record_fn` (required).
- STOP messages are consumed and not recorded.
"""

from typing import Callable, Any
import traceback
from dsl.core import SimpleAgent, STOP

# =================================================
#                    Sink(SimpleAgent)
# =================================================

RecordFn = Callable[[SimpleAgent, Any], None]


class Sink(SimpleAgent):
    """
    A terminal agent that consumes messages.

    Parameters
    ----------
    name : str
        Agent name.
    record_fn : RecordFn
        Callback invoked for each non-STOP message as (agent, msg).
    """

    def __init__(
        self,
        name: str = "Sink",
        record_fn: RecordFn = None,  # type: ignore[assignment]
    ):
        if record_fn is None:
            raise ValueError("record_fn is required for Sink")

        self.record_fn: RecordFn = record_fn

        def _handle_msg(agent: SimpleAgent, msg: Any) -> None:
            # Consume STOP silently
            if msg == STOP:
                return
            # Record
            try:
                self.record_fn(agent, msg)
            except Exception:
                # Avoid crashing the agent loop on user callback errors
                with open("dsl_debug.log", "a") as log:
                    log.write(f"\n--- {self.__class__.__name__} Error ---\n")
                    log.write(traceback.format_exc())

        super().__init__(
            name=name,
            inport="in",
            outports=[],
            handle_msg=_handle_msg,
        )
