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
        func: Callable[..., Any],
        args: Optional[tuple] = (),
        kwargs: Optional[dict] = None,
        name: str = "Transform",
    ):
        if func is None:
            raise ValueError("Transform requires a callable func(msg, ...)")
        self.func = func
        self.args = args or ()
        self.kwargs = kwargs or {}

        def _handle_msg(agent, msg):
            if msg is STOP:
                agent.send(STOP, "out")
                return
            result = self.func(msg, *self.args, **self.kwargs)
            agent.send(result, "out")

        super().__init__(
            name=name,          # SimpleAgent stores .name for you
            inport="in",
            outports=["out"],
            handle_msg=_handle_msg,
        )

    def __repr__(self) -> str:
        fn = getattr(self.func, "__name__", repr(self.func))
        return f"Transform(name={self.name!r}, func={fn}, args={self.args}, kwargs={self.kwargs})"

    def __str__(self) -> str:
        return f"{self.name} (Transform)"
