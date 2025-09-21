# dsl/blocks/source.py

from __future__ import annotations
import traceback
from typing import Any, Callable, Iterator, Iterable, Union
from dsl.core import Agent, STOP


class Source(Agent):
    """
    Inports: [], Outports: ["out"].
    Accepts a factory, iterator, or iterable; normalized internally to a zero-arg factory.
    Runtime contract: factory() -> iterator/generator. Emits STOP when exhausted or on error.
    """

    def __init__(
        self,
        *,
        fn: Union[Callable[[], Iterator[Any]], Iterator[Any], Iterable[Any]],
    ) -> None:
        if fn is None:
            raise ValueError("Source requires a factory/iterator/iterable")
        super().__init__(inports=[], outports=["out"])

        # Normalize to a zero-arg factory; warn once if a single-use iterator is reused.
        self._warned_reuse = False

        if callable(fn):  # user-supplied factory
            self._factory: Callable[[], Iterator[Any]] = fn

        elif hasattr(fn, "__next__"):  # iterator (single-use)
            iterator = fn  # type: ignore[assignment]
            used = {"v": False}

            def _factory_single_use() -> Iterator[Any]:
                if used["v"] and not self._warned_reuse:
                    print(
                        "[Source] Warning: reusing a single-use iterator; it may already be exhausted.")
                    self._warned_reuse = True
                used["v"] = True
                return iterator  # type: ignore[return-value]

            self._factory = _factory_single_use

        elif hasattr(fn, "__iter__"):  # iterable → fresh iterator each run
            iterable = fn  # capture

            def _factory_from_iterable() -> Iterator[Any]:
                return iter(iterable)

            self._factory = _factory_from_iterable

        else:
            raise TypeError(
                f"Unsupported type for Source: {type(fn).__name__}")

    # -------- Optional convenience constructors --------
    @classmethod
    def from_factory(cls, factory: Callable[[], Iterator[Any]]) -> "Source":
        return cls(fn=factory)

    @classmethod
    def from_iterator(cls, it: Iterator[Any]) -> "Source":
        return cls(fn=it)

    @classmethod
    def from_iterable(cls, iterable: Iterable[Any]) -> "Source":
        return cls(fn=iterable)

    # ------------------------------ Runtime ------------------------------
    def run(self) -> None:
        try:
            it = self._factory()
            if not (hasattr(it, "__iter__") and hasattr(it, "__next__")):
                raise TypeError(
                    f"Source factory must return an iterator/generator, got {type(it).__name__}"
                )
            for item in it:
                # None=drop (do not emit)
                if item is None:
                    continue
                # Forbid user-yielded STOP to avoid double-STOP at merges
                if item == STOP:
                    print(
                        "[Source] Error: user function yielded STOP; terminating stream.")
                    break
                self.send(item, "out")
            self.send(STOP, "out")
        except Exception as e:
            try:
                print(f"[Source] Error: {e}")
                print(traceback.format_exc())
            finally:
                self.send(STOP, "out")


__all__ = ["Source"]
