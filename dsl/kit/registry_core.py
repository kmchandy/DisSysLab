# dsl/registry_core.py
from __future__ import annotations
from dataclasses import dataclass, field
from functools import wraps
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple

# What authors attach to functions (no dependency on catalog)


@dataclass(frozen=True)
class Registration:
    kind: str                        # "source" | "transform" | "sink"
    help: str
    param_schema: Dict[str, Any]
    default_shape: Dict[str, Any]


# Functions decorated before the catalog adopts them land here
_PENDING: List[Tuple[str, Registration, Callable[..., Any]]] = []


def register(
    *, kind: str = None, help: str = "",
    param_schema: Dict[str, Any] | None = None,
    default_shape: Dict[str, Any] | None = None,
):
    if kind not in {"source", "transform", "sink"}:
        raise ValueError(
            f"register(kind=...) must be 'source'|'transform'|'sink', got {kind!r}")
    reg = Registration(
        kind=kind, help=help,
        param_schema=param_schema or {}, default_shape=default_shape or {}
    )

    def deco(fn: Callable[..., Any]):
        # Attach metadata for introspection and queue it
        setattr(fn, "__dsl_registration__", reg)
        _PENDING.append((fn.__name__, reg, fn))
        return fn
    return deco


def pop_pending_registrations() -> List[Tuple[str, Registration, Callable[..., Any]]]:
    items = list(_PENDING)
    _PENDING.clear()
    return items


def as_factory(f: Callable[..., Iterator[Any]]) -> Callable[..., Callable[[], Iterator[Any]]]:
    @wraps(f)
    def wrapper(*args, **kwargs) -> Callable[[], Iterator[Any]]:
        def _factory() -> Iterator[Any]:
            return f(*args, **kwargs)  # returns the iterator
        return _factory
    return wrapper
