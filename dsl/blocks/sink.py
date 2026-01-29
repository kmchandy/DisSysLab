# dsl/blocks/sink.py
"""
Sink Agent: Consumes messages for side effects.

Sinks have one input and no outputs. They are terminal nodes that call
fn(msg, **params) for each message to perform side effects like printing,
saving, or collecting.
"""

from __future__ import annotations
from typing import Any, Callable, Optional, Dict
import traceback

from dsl.core import Agent, STOP


class Sink(Agent):
    """
    Sink agent: consumes messages for side effects.
    
    Single input, no outputs. Terminal node that calls fn(msg, **params)
    for each message. Used for actions like printing, saving, or sending.
    
    **Ports:**
    - Inports: ["in_"]
    - Outports: [] (no outputs)
    
    **Message Flow:**
    - Receives msg from "in_" port
    - Calls fn(msg, **params)
    - No outputs (terminal node)
    - Terminates on STOP
    
    **Error Handling:**
    - Exceptions caught, logged, pipeline stopped
    - Fail-fast for educational clarity
    
    **Examples:**
    
    Print to console:
        >>> sink = Sink(fn=print, name="printer")
    
    Collect results:
        >>> results = []
        >>> sink = Sink(fn=results.append, name="collector")
    
    Save to file:
        >>> def save_to_file(msg):
        ...     with open("output.txt", "a") as f:
        ...         f.write(str(msg) + "\\n")
        >>> sink = Sink(fn=save_to_file, name="writer")
    
    With parameters:
        >>> def save_json(msg, filename):
        ...     with open(filename, "a") as f:
        ...         json.dump(msg, f)
        ...         f.write("\\n")
        >>> sink = Sink(fn=save_json, params={"filename": "data.jsonl"}, name="saver")
    """
    
    def __init__(
        self,
        *,
        fn: Callable[..., None],
        name: str,
        params: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize Sink agent.
        
        Args:
            fn: Callable that processes messages for side effects.
                Signature: fn(msg, **params) -> None
                - Takes message and optional keyword arguments
                - Return value ignored (side effects only)
            name: Unique name for this agent (REQUIRED)
            params: Optional dict of keyword arguments passed to fn
        
        Raises:
            ValueError: If name is empty
            TypeError: If fn is not callable
        """
        if not name:
            raise ValueError("Sink agent requires a name")
        
        if not callable(fn):
            raise TypeError(
                f"Sink fn must be callable, got {type(fn).__name__}"
            )
        
        super().__init__(name=name, inports=["in_"], outports=[])
        self._fn = fn
        self._params = params or {}
    
    @property
    def default_inport(self) -> str:
        """Default input port for edge syntax."""
        return "in_"
    
    def run(self) -> None:
        """
        Process messages until STOP.
        
        Calls fn for each message, terminates on STOP.
        """
        while True:
            # Receive message
            msg = self.recv("in_")
            
            # Check for termination
            if msg is STOP:
                # No outputs to broadcast to
                return
            
            # Process message for side effects
            try:
                self._fn(msg, **self._params)
            except Exception as e:
                # Fail-fast: log error and stop
                print(f"[Sink '{self.name}'] Error in fn: {e}")
                print(traceback.format_exc())
                # No broadcast_stop() - we have no outputs
                return
    
    def __repr__(self) -> str:
        fn_name = getattr(self._fn, "__name__", repr(self._fn))
        return f"<Sink name={self.name} fn={fn_name}>"

    def __str__(self) -> str:
        return "Sink"