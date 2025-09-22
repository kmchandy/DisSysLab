# dsl/utils/params.py
from __future__ import annotations
import inspect
from typing import Any, Mapping, Dict


def filter_kwargs(fn: Any, pool: Mapping[str, Any] | None) -> Dict[str, Any]:
    """
    Return a dict containing only keys that `fn` accepts as kwargs.
    If `fn` accepts **kwargs or signature introspection fails, return all of `pool`.
    """
    if not pool:
        return {}
    try:
        sig = inspect.signature(fn)
    except (TypeError, ValueError):
        return dict(pool)
    params = sig.parameters.values()
    if any(p.kind == p.VAR_KEYWORD for p in params):
        return dict(pool)
    allowed = {
        p.name
        for p in params
        if p.kind in (inspect.Parameter.POSITIONAL_OR_KEYWORD, inspect.Parameter.KEYWORD_ONLY)
    }
    return {k: v for k, v in pool.items() if k in allowed}
