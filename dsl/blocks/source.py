# dsl.block_lib.sources.source.py

from __future__ import annotations
import traceback
from typing import Any, Callable, Iterator, Optional, Dict
from dsl.core import Agent, STOP


class Source(Agent):
    """
    Inports: [], Outports: ["out"]
    Calls a user-supplied generator function 'fn' and sends each yielded item on "out".
    Contract: fn() -> iterator/generator.
    Sends STOP on "out" when the generator is exhausted or on error.
    """

    def __init__(
        self,
        *,
        fn: Callable[..., Iterator[Any]],
        kwargs: Any = None
    ) -> None:
        if fn is None:
            raise ValueError(
                "Source requires a fn (iterator/generator)")
        super().__init__(inports=[], outports=["out"])
        self._fn = fn
        self.kwargs = kwargs if kwargs is not None else {}

    def run(self) -> None:
        try:
            _iterator = self._fn()  # Must return an iterator
            if (not hasattr(_iterator, "__iter__") or
                    not hasattr(_iterator, "__next__")):
                raise TypeError(
                    f"Source fn() must return an iterator/generator, got {type(_iterator).__name__}"
                )
            for item in _iterator:
                self.send(item, "out")
            self.send(STOP, "out")
        except Exception as e:
            try:
                print(f"[Source] Error: {e}")
                print(traceback.format_exc())
            finally:
                self.send(STOP, "out")


__all__ = ["Source"]
