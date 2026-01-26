# dsl/blocks/transform.py
"""
Transform Agent: Applies a function to transform messages.

Transforms have one input and one output. They process each message by
calling fn(msg, **params) and sending the result downstream.
"""

from __future__ import annotations
from typing import Any, Callable, Optional, Dict
import traceback

from dsl.core import Agent, STOP


class Transform(Agent):
    """
    Transform agent: applies a function to each message.
    
    Single input, single output. Processes each message by calling
    fn(msg, **params) and sending the result.
    
    **Ports:**
    - Inports: ["in_"]
    - Outports: ["out_"]
    
    **Message Flow:**
    - Receives msg from "in_" port
    - Calls fn(msg, **params)
    - Sends result to "out_" port
    - If fn returns None, message is filtered (not sent)
    - Forwards STOP and terminates
    
    **Error Handling:**
    - Exceptions caught, logged, pipeline stopped
    - Fail-fast for educational clarity
    
    **Examples:**
    
    Simple transform:
        >>> def double(x):
        ...     return x * 2
        >>> transform = Transform(fn=double, name="doubler")
    
    With parameters:
        >>> def scale(x, factor):
        ...     return x * factor
        >>> transform = Transform(fn=scale, params={"factor": 10}, name="scaler")
    
    Stateful transform (instance method):
        >>> class Counter:
        ...     def __init__(self):
        ...         self.count = 0
        ...     def process(self, msg):
        ...         self.count += 1
        ...         return {"value": msg, "index": self.count}
        >>> counter = Counter()
        >>> transform = Transform(fn=counter.process, name="counter")
    
    Filter pattern:
        >>> def filter_positive(x):
        ...     return x if x > 0 else None
        >>> transform = Transform(fn=filter_positive, name="filter")
    """
    
    def __init__(
        self,
        *,
        fn: Callable[..., Optional[Any]],
        name: str,
        params: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize Transform agent.
        
        Args:
            fn: Callable that transforms messages.
                Signature: fn(msg, **params) -> result
                - Takes message and optional keyword arguments
                - Returns transformed message, or None to filter
            name: Unique name for this agent (REQUIRED)
            params: Optional dict of keyword arguments passed to fn
        
        Raises:
            ValueError: If name is empty
            TypeError: If fn is not callable
        """
        if not name:
            raise ValueError("Transform agent requires a name")
        
        if not callable(fn):
            raise TypeError(
                f"Transform fn must be callable, got {type(fn).__name__}"
            )
        
        super().__init__(name=name, inports=["in_"], outports=["out_"])
        self._fn = fn
        self._params = params or {}
    
    @property
    def default_inport(self) -> str:
        """Default input port for edge syntax."""
        return "in_"
    
    @property
    def default_outport(self) -> str:
        """Default output port for edge syntax."""
        return "out_"
    
    def run(self) -> None:
        """
        Process messages in loop.
        
        Receives messages, transforms them, sends results.
        Stops on STOP signal or exception.
        """
        while True:
            # Receive message
            msg = self.recv("in_")
            
            # Check for termination
            if msg is STOP:
                self.broadcast_stop()
                return
            
            # Transform message
            try:
                result = self._fn(msg, **self._params)
            except Exception as e:
                # Fail-fast: log error and stop pipeline
                print(f"[Transform '{self.name}'] Error in fn: {e}")
                print(traceback.format_exc())
                self.broadcast_stop()
                return
            
            # Send result (None filtered automatically by send())
            self.send(result, "out_")
    
    def __repr__(self) -> str:
        fn_name = getattr(self._fn, "__name__", repr(self._fn))
        return f"<Transform name={self.name} fn={fn_name}>"

    def __str__(self) -> str:
        return "Transform"