from __future__ import annotations

import time
from datetime import datetime
import traceback
from typing import Any, Callable, Iterator, Optional, List, Dict, Union

# your strict, iterator-only class
from dsl.block_lib.stream_generators import StreamGenerator
from dsl.core import Agent, STOP


# ----------------------------------------
#             StreamGenerator           |
# ----------------------------------------

class StreamGenerator(Agent):
    """
    PORTS
    -----
    Inports:   []
    Outports:  ["out"]

    ROLE
    ----
    The agent calls a user-supplied *generator function*
    and sends every yielded item on outport "out".

    PARAMETERS
    ----------
    generator_fn : Callable[..., Iterator[Any]]   (REQUIRED)
        A function that returns a generator/iterator.

    name : str = "StreamGenerator"
        Name (shown in logs/diagrams).

    delay : float | None
        Seconds to sleep after each send.

    **gen_kwargs : dict
        Passed through to `generator_fn`.

    BEHAVIOR
    --------
    - `generator_fn(**gen_kwargs)` must return a Python generator/iterator.
    - Each item yielded by generator_fn is sent as a message on 'out'.
    - After the generator is exhausted, the block sends STOP and returns.

    ERROR HANDLING
    --------------
    - Any exception is printed and appended to 'dsl_debug.log'.
    - On error, the block sends STOP and returns (fails closed).

    EXAMPLES
    --------
    # 1) Dict messages (text/NLP)
    def lines():
        yield {"text": "hello"}
        yield {"text": "world"}
    src = StreamGenerator(generator_fn=lines)

    # 2) Numeric messages (NumPy/ML)
    def rows():
        for i in range(3):
            yield i  # or a numpy row
    src = StreamGenerator(generator_fn=rows, delay=0.01)

    """

    def __init__(
        self,
        *,
        generator_fn: Callable[..., Iterator[Any]],
        name: Optional[str] = "StreamGenerator",
        delay: Optional[float] = None,
        **gen_kwargs: Any,
    ) -> None:
        if generator_fn is None:
            raise ValueError(
                "StreamGenerator requires a generator_fn returning a generator/iterator")

        super().__init__(
            name=name or "StreamGenerator",
            inports=[],
            outports=["out"],
            run=self.run,
        )

        self._generator_fn = generator_fn
        self._gen_kwargs: Dict[str, Any] = dict(gen_kwargs)
        self._delay = float(delay) if delay else None

    def run(self) -> None:
        try:
            items = self._generator_fn(
                **self._gen_kwargs)  # must be an iterator

            # ensure that items is an iterator/generator
            try:
                items = iter(items)
            except TypeError:
                raise TypeError(
                    f"{self.__class__.__name__} expected generator_fn() to return a generator/iterator, "
                    f"got {type(items).__name__}."
                )

            # Send each item yielded by the generator on outport "out".
            for item in items:
                self.send(item, "out")
                if self._delay:
                    time.sleep(self._delay)

            # Finished sending all messages; so send STOP.
            self.send(STOP, "out")

        except Exception as e:
            print(f"[{self.__class__.__name__}] Error: {e}")
            try:
                with open("dsl_debug.log", "a") as log:
                    log.write(f"\n--- {self.__class__.__name__} Error ---\n")
                    log.write(traceback.format_exc())
            finally:
                self.send(STOP, "out")
