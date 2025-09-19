# dsl/block_lib/transformers/transform.py
from __future__ import annotations
from typing import Any, Callable, Optional
from dsl.core import SimpleAgent, STOP


class Transform(SimpleAgent):
    """
    Minimal transform:
    - Passes STOP through unchanged.
    - Applies self.func(msg, *self.args, **self.kwargs) and emits the result on 'out'.
    """

    def __init__(
        self,
        *,
        func: Callable[..., Any],
        name: str = "Transform",
        args: Optional[tuple] = (),
        kwargs: Optional[dict] = {},
    ):
        if func is None:
            raise ValueError("Transform requires a callable func(msg, ...)")
        self.func = func
        self.args = args or ()
        self.kwargs = kwargs or {}

        super().__init__(
            name=name or "Transform",
            inport="in",
            outports=["out"],
        )

    def __repr__(self) -> str:
        fn = getattr(self.func, "__name__", repr(self.func))
        return f"Transform(name={self.name!r}, func={fn})"

    def __str__(self) -> str:
        return f"{self.name} (Transform)"

    def handle_msg(self, msg):
        if msg is STOP:
            self.send(STOP, "out")
            return
        result = self.func(msg, *self.args, **self.kwargs)
        self.send(result, "out")
