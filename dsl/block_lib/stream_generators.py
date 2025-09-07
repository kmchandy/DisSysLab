from __future__ import annotations

import time
import traceback
from typing import Any, Callable, Iterator, Optional, Dict

from dsl.core import Agent
from dsl.core import STOP


class StreamGenerator(Agent):
    """
    PORTS
    -----
    Inports:   []
    Outports:  ["out"]

    ROLE
    ----
    A source block driven by `run()`. It calls a user-supplied *generator function*
    and forwards every yielded item on outport "out".

    CONTRACT (generators only)
    --------------------------
    - `generator_fn(**gen_kwargs)` **must return a Python generator** (or any
      Iterator[Any]). No lists, tuples, or singletons are accepted here.
      (See helper constructors below for those cases.)
    - Each yielded item is sent as a message.
    - After the generator is exhausted, the block emits STOP and returns.

    WRAPPING (optional)
    -------------------
    - If `key` is not None, each item is wrapped as `{key: item}`.
    - If `key` is None, each item is forwarded as-is.

    PARAMETERS
    ----------
    generator_fn : Callable[..., Iterator[Any]]   (REQUIRED)
        A function that returns a generator/iterator.

    name : str = "StreamGenerator"
        Friendly name (shown in logs/diagrams).

    delay : float | None
        Seconds to sleep **after each send** (simple throttling).

    key : str | None
        If provided, wrap each yielded item as `{key: item}`; otherwise forward.

    **gen_kwargs : dict
        Passed through to `generator_fn`.
    """

    def __init__(
        self,
        *,
        generator_fn: Callable[..., Iterator[Any]],
        name: Optional[str] = "StreamGenerator",
        delay: Optional[float] = None,
        key: Optional[str] = None,
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
        self._wrap_key = key

    # ----- main loop -----

    def run(self) -> None:
        try:
            items = self._generator_fn(
                **self._gen_kwargs)  # must be an iterator
            # Optional defensive check
            if not hasattr(it, "__iter__") or not hasattr(it, "__next__"):
                raise TypeError(
                    f"{self.__class__.__name__} expected generator_fn() to return a generator/iterator, "
                    f"got {type(it).__name__}."
                )

            for item in items:
                msg = {self._wrap_key: item} if self._wrap_key else item
                self.send(msg, "out")
                if self._delay:
                    time.sleep(self._delay)
            # Finished sending all msgs in generator_fn. So STOP.
            self.send(STOP, "out")

        except Exception as e:
            print(f"[{self.__class__.__name__}] Error: {e}")
            try:
                with open("dsl_debug.log", "a") as log:
                    log.write(f"\n--- {self.__class__.__name__} Error ---\n")
                    log.write(traceback.format_exc())
            finally:
                self.send(STOP, "out")
