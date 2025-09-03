# dsl/block_lib/stream_transformers.py
from __future__ import annotations
from typing import Any, Callable, Optional, Dict
from dsl.core import SimpleAgent


class TransformerFunction(SimpleAgent):
    """
    Wrap a Python function as a block that transforms messages.

    - If input_key/output_key are given and msg is a dict:
        * read input value from msg[input_key]
        * write result to msg[output_key] (copy-on-write)
      Otherwise, treat msg itself as the value and emit the raw result.

    Example:
        tf = TransformerFunction(func=str.upper)
        tf will output "HELLO" for input "hello".
    """

    def __init__(
        self,
        *,
        func: Callable[[Any], Any],
        input_key: Optional[str] = None,
        output_key: Optional[str] = None,
        name: Optional[str] = "TransformerFunction",
    ) -> None:
        if not callable(func):
            raise TypeError("func must be callable")
        self._func = func
        self._in_key = input_key
        self._out_key = output_key

        # NOTE: instance-assigned handler → no implicit self
        def _handle(msg: Any, **_params: Dict[str, Any]) -> None:
            # dict routing
            if isinstance(msg, dict) and (self._in_key is not None or self._out_key is not None):
                if self._in_key is None or self._out_key is None:
                    raise ValueError(
                        f"{name}: both input_key and output_key must be set when using dict routing"
                    )
                if self._in_key not in msg:
                    raise KeyError(
                        f"{name}: input_key '{self._in_key}' not in message dict")
                value_in = msg[self._in_key]
                value_out = self._func(value_in)
                new_msg = dict(msg)
                new_msg[self._out_key] = value_out
                self.send(new_msg, outport="out")
                return

            # plain message routing
            result = self._func(msg)
            self.send(result, outport="out")

        super().__init__(name=name, inport="in",
                         outports=["out"], handle_msg=_handle)
