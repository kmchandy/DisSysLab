# dsl/kit/api.py
from __future__ import annotations

from typing import Any, Callable, Optional, Dict

from dsl.blocks.source import Source
from dsl.blocks.sink import Sink

# Transform is optional until implemented
try:
    from dsl.blocks.transform import Transform  # type: ignore
except Exception:  # pragma: no cover
    Transform = None  # type: ignore


def generate(fn: Any, **params: Any) -> Source:
    """
    Wrap a source function/iterable/iterator as a Source block.
    Usage mirrors v2 unified signature:
      generate(from_list, items=["hello","world"])
    """
    return Source(fn=fn, params=params or None)


def transform(fn: Callable[..., Any], **params: Any):
    """
    Wrap a transform function as a Transform block (msg, **params) -> Any.
    Returns a block that drops None and forwards everything else.
    """
    if Transform is None:  # pragma: no cover
        raise ImportError(
            "Transform block not available (dsl.blocks.transform.Transform missing). "
            "Implement it before calling kit.transform()."
        )
    return Transform(fn=fn, params=params or None)


def record(fn: Callable[..., Any], **params: Any) -> Sink:
    """
    Wrap a sink function as a Sink block (msg, **params) -> Any.
    """
    return Sink(fn=fn, params=params or None)


__all__ = ["generate", "transform", "record"]
