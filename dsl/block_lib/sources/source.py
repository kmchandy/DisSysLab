from __future__ import annotations
import traceback
from typing import Any, Callable, Iterator, Optional, Dict
from dsl.core import Agent, STOP


class Source(Agent):
    """
    Inports: [], Outports: ["out"]
    Calls a user-supplied generator function and sends each yielded item on "out".
    Contract: generator_fn(**gen_kwargs) must return a Python iterator/generator.
    Sends STOP on "out" when the generator is exhausted or on error.
    """

    def __init__(
        self,
        *,
        generator_fn: Callable[..., Iterator[Any]],
        name: Optional[str] = "Source",
        **gen_kwargs: Any,
    ) -> None:
        if generator_fn is None:
            raise ValueError(
                "Source requires a generator_fn (iterator/generator)")
        super().__init__(name=name or "Source", inports=[], outports=["out"], run=self.run)
        self._generator_fn = generator_fn
        self._gen_kwargs: Dict[str, Any] = dict(gen_kwargs)

    def run(self) -> None:
        try:
            items = self._generator_fn(**self._gen_kwargs)
            for item in items:
                self.send(item, "out")
            self.send(STOP, "out")
        except Exception as e:
            print(f"[{self.__class__.__name__}] Error: {e}")
            try:
                with open("dsl_debug.log", "a") as log:
                    log.write(f"\n--- {self.__class__.__name__} Error ---\n")
                    log.write(traceback.format_exc())
            finally:
                self.send(STOP, "out")


__all__ = ["Source"]
