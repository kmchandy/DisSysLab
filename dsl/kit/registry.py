# dsl/registry.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Callable, Dict, Tuple, Optional

Kind = str  # "source" | "transform" | "sink"
RegistryMap = Dict[str, Tuple["Registration", Callable[..., Any]]]


@dataclass(frozen=True)
class Registration:
    kind: Kind                    # "source" | "transform" | "sink"
    help: str = ""
    param_schema: Dict[str, Any] = None  # advisory only


def manual_register(
    *,
    registry: RegistryMap,
    id: str,
    kind: Kind,
    fn: Callable[..., Any],
    help: str = "",
    param_schema: Optional[Dict[str, Any]] = None,
) -> None:
    if kind not in {"source", "transform", "sink"}:
        raise ValueError(
            f"kind must be 'source'|'transform'|'sink', got {kind!r}")
    reg = Registration(kind=kind, help=help, param_schema=param_schema or {})
    if id in registry:
        existing_reg, existing_fn = registry[id]
        if existing_fn is not fn or existing_reg.kind != reg.kind:
            raise ValueError(f"Registry id conflict for '{id}'")
        return  # idempotent re-register
    # attach metadata for optional introspection
    setattr(fn, "__dsl_registration__", reg)
    setattr(fn, "__dsl_registration_id__", id)
    registry[id] = (reg, fn)


def resolve(registry: RegistryMap, id: str) -> Tuple[Registration, Callable[..., Any]]:
    return registry[id]
