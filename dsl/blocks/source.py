# dsl/blocks/source.py

from __future__ import annotations
import traceback
import inspect
from typing import Any, Callable, Iterator, Iterable, Union, Optional, Dict
from dsl.utils import filter_kwargs
from dsl.core import Agent, STOP


class Source(Agent):
    """
    Inports: [], Outports: ["out"].
    Unified constructor: `Source(fn, params=None)`.
      - If `fn` is callable: we call `fn(**params)` to obtain an iterator (factory form).
      - If `fn` is an iterable: we use `iter(fn)` per run.
      - If `fn` is an iterator: single-use; later runs may yield nothing (warn once).
    Emits STOP when exhausted or on error. Drops `None`. Forbids user-yielded STOP.
    """

    def __init__(
        self,
        *,
        fn: Union[Callable[..., Iterator[Any]], Iterator[Any], Iterable[Any]],
        params: Optional[Dict[str, Any]] = None,
    ) -> None:
        if fn is None:
            raise ValueError("Source requires a factory/iterator/iterable")
        super().__init__(inports=[], outports=["out"])

        self._warned_reuse = False  # for single-use iterator reuse
        self._factory: Callable[[], Iterator[Any]]

        if callable(fn):
            kwargs = filter_kwargs(fn, params)
            self._factory = lambda: fn(**kwargs)  # type: ignore[misc]
        elif hasattr(fn, "__next__"):  # iterator (single-use)
            if params:
                print("[Source] Warning: params ignored for iterator-based Source.")
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
            if params:
                print("[Source] Warning: params ignored for iterable-based Source.")
            iterable = fn  # capture
            self._factory = lambda: iter(iterable)  # type: ignore[arg-type]
        else:
            raise TypeError(
                f"Unsupported type for Source: {type(fn).__name__}")

    # Optional convenience constructors
    @classmethod
    def from_factory(cls, factory: Callable[..., Iterator[Any]], **params: Any) -> "Source":
        return cls(fn=factory, params=params or None)

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
                if isinstance(item, str) and item == STOP:
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
