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
        gen_kwargs: Any = None
    ) -> None:
        if generator_fn is None:
            raise ValueError(
                "Source requires a generator_fn (iterator/generator)")
        super().__init__(inports=[], outports=["out"])
        self.generator_fn = generator_fn
        self.gen_kwargs = gen_kwargs if gen_kwargs is not None else {}

    def run(self) -> None:
        print(f"starting run() of {self.__class__.__name__}")
        print(f"self.gen_kwargs = {self.gen_kwargs}")
        try:
            print(f"calling generator function {self.generator_fn}")
            print(f"self.gen_kwargs = {self.gen_kwargs}")
            items = self.generator_fn()
            # items = self.generator_fn(**self.gen_kwargs)
            for item in items:
                self.send(item, "out")
            self.send(STOP, "out")
        except Exception as e:
            try:
                print(f"\n--- {self.__class__.__name__} Error ---\n")
            finally:
                self.send(STOP, "out")


__all__ = ["Source"]
