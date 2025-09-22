# dsl/registry.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple
import importlib.util
import inspect
import types
from pathlib import Path
from dsl.registry import manual_register, RegistryMap, Registration

# Public types
Kind = str  # "source" | "transform" | "sink"
RegistryMap = Dict[str, Tuple["Registration", Callable[..., Any]]]


@dataclass(frozen=True)
class Registration:
    kind: Kind                    # "source" | "transform" | "sink"
    help: str = ""
    param_schema: Dict[str, Any] = None  # optional, advisory only


# pending items captured by @register before adoption
_PENDING: List[Tuple[str, Registration, Callable[..., Any]]] = []


def _default_id(fn: Callable[..., Any]) -> str:
    # Stable, fully-qualified id
    return f"{fn.__module__}:{fn.__name__}"


def register(
    *,
    kind: Kind,
    id: Optional[str] = None,
    help: str = "",
    param_schema: Optional[Dict[str, Any]] = None,
):
    """
    Decorator: attach metadata and queue the function for later adoption.
    Usage:
        @register(kind="source")           # id defaults to module:name
        def from_list(...): ...
        @register(kind="sink", id="lists:record_to_list")
        def record_to_list(...): ...
    """
    if kind not in {"source", "transform", "sink"}:
        raise ValueError(
            f"register(kind=...) must be 'source'|'transform'|'sink', got {kind!r}")

    def deco(fn: Callable[..., Any]):
        rid = id or _default_id(fn)
        reg = Registration(kind=kind, help=help,
                           param_schema=param_schema or {})
        setattr(fn, "__dsl_registration__", reg)
        setattr(fn, "__dsl_registration_id__", rid)
        _PENDING.append((rid, reg, fn))
        return fn

    return deco


def pop_pending_registrations() -> List[Tuple[str, Registration, Callable[..., Any]]]:
    """Return and clear the current pending list."""
    items = list(_PENDING)
    _PENDING.clear()
    return items


def adopt_pending_into(registry: RegistryMap) -> RegistryMap:
    """
    Move all pending registrations into `registry`.
    - On id conflict with a different function or kind, raise ValueError.
    - Re-adding the *same* function idempotently is allowed.
    """
    for rid, reg, fn in pop_pending_registrations():
        if rid in registry:
            existing_reg, existing_fn = registry[rid]
            if existing_fn is not fn or existing_reg.kind != reg.kind:
                raise ValueError(f"Registry id conflict for '{rid}'")
            # idempotent: same fn/kind; keep existing
            continue
        registry[rid] = (reg, fn)
    return registry


def manual_register(
    *,
    registry: RegistryMap,
    id: str,
    kind: Kind,
    fn: Callable[..., Any],
    help: str = "",
    param_schema: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Directly add a callable to the registry without using the decorator.
    Raises on id conflict with a different function or kind.
    """
    if kind not in {"source", "transform", "sink"}:
        raise ValueError(
            f"kind must be 'source'|'transform'|'sink', got {kind!r}")
    reg = Registration(kind=kind, help=help, param_schema=param_schema or {})
    if id in registry:
        existing_reg, existing_fn = registry[id]
        if existing_fn is not fn or existing_reg.kind != reg.kind:
            raise ValueError(f"Registry id conflict for '{id}'")
        return  # idempotent
    setattr(fn, "__dsl_registration__", reg)
    setattr(fn, "__dsl_registration_id__", id)
    registry[id] = (reg, fn)


def resolve(registry: RegistryMap, id: str) -> Tuple[Registration, Callable[..., Any]]:
    """Lookup by id; raise KeyError if missing."""
    return registry[id]


def _load_module_from_path(path: str | Path, name: Optional[str] = None) -> types.ModuleType:
    p = Path(path)
    mod_name = name or p.stem
    spec = importlib.util.spec_from_file_location(mod_name, str(p))
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load module from {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _iter_public_callables(mod: types.ModuleType) -> Iterable[Tuple[str, Callable[..., Any]]]:
    for k, v in vars(mod).items():
        if k.startswith("_"):
            continue
        if inspect.isfunction(v) or inspect.isbuiltin(v):
            yield k, v


def register_functions_in_module(
    *,
    registry: RegistryMap,
    module: types.ModuleType,
    kind: str,                         # "source" | "transform" | "sink"
    # prefix for ids; default = module.__name__
    namespace: Optional[str] = None,
    include: Optional[Iterable[str]] = None,
    exclude: Optional[Iterable[str]] = None,
    # optional per-fn help text
    help_fn: Optional[Callable[[str, Callable[..., Any]], str]] = None,
) -> List[str]:
    if kind not in {"source", "transform", "sink"}:
        raise ValueError(f"kind must be source|transform|sink, got {kind}")
    inc = set(include) if include else None
    exc = set(exclude) if exclude else set()
    ns = namespace or module.__name__
    registered: List[str] = []
    for name, fn in _iter_public_callables(module):
        if inc is not None and name not in inc:
            continue
        if name in exc:
            continue
        rid = f"{ns}:{name}"
        manual_register(
            registry=registry,
            id=rid,
            kind=kind,
            fn=fn,
            help=help_fn(name, fn) if help_fn else "",
            param_schema=None,
        )
        registered.append(rid)
    return registered


def register_functions_in_file(
    *,
    registry: RegistryMap,
    path: str | Path,
    kind: str,
    namespace: Optional[str] = None,
    include: Optional[Iterable[str]] = None,
    exclude: Optional[Iterable[str]] = None,
    module_name: Optional[str] = None,
    help_fn: Optional[Callable[[str, Callable[..., Any]], str]] = None,
) -> List[str]:
    """Load a Python file (no DSL imports inside required) and register its public functions."""
    mod = _load_module_from_path(path, name=module_name)
    ns = namespace or getattr(mod, "__name__", Path(path).stem)
    return register_functions_in_module(
        registry=registry,
        module=mod,
        kind=kind,
        namespace=ns,
        include=include,
        exclude=exclude,
        help_fn=help_fn,
    )
