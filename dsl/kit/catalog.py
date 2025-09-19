# dsl/kit/catalog.py
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Tuple, Union

from dsl.registry_core import Registration, pop_pending_registrations

CATALOG_VERSION = "kit.curated@0.1.0"


@dataclass(frozen=True)
class CatalogEntry:
    kind: str  # "source" | "transform" | "sink"
    callable: Callable[..., Any]
    help: str = ""  # short description
    param_schema: dict[str, any] = field(default_factory=dict)  # JSON Schema
    default_shape: dict[str, any] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
    aliases: list[str] = field(default_factory=list)
    io: dict[str, any] = field(default_factory=dict)
    example: str = ""


# name -> metadata
CATALOG: Dict[str, CatalogEntry] = {}


def adopt_from_registry_core() -> None:
    for name, reg, fn in pop_pending_registrations():
        CATALOG[name] = CatalogEntry(
            kind=reg.kind,
            callable=fn,
            help=reg.help,
            param_schema=reg.param_schema,
            default_shape=reg.default_shape,
            tags=reg.tags,
            aliases=reg.aliases,
            io=reg.io,
            example=reg.example,
        )


def view_funcs() -> Dict[str, Callable[..., Any]]:
    """Convenience: name -> callable view (FN)."""
    return {name: entry.callable for name, entry in CATALOG.items()}


def resolve_name_or_callable(
    x: Union[str, Callable[..., Any]],
    expected_kind: str | None = None
) -> Tuple[Callable[..., Any], str, str]:
    """
    Resolve either a catalog name or a callable.
    Returns (callable, kind, name).
    If expected_kind is provided, enforce it.
    """
    if isinstance(x, str):
        entry = CATALOG.get(x)
        if not entry:
            suggestions = ", ".join(sorted(CATALOG.keys()))
            raise KeyError(f"Unknown function '{x}'. Known: {suggestions}")
        if expected_kind and entry.kind != expected_kind:
            raise TypeError(
                f"Function '{x}' is kind '{entry.kind}', expected '{expected_kind}'.")
        return entry.callable, entry.kind, x
    # Callable provided directly; we won't have kind/name unless it was registered.
    # Try to find it in the catalog by identity; otherwise mark as 'unknown'.
    for name, entry in CATALOG.items():
        if entry.callable is x:
            if expected_kind and entry.kind != expected_kind:
                raise TypeError(
                    f"Callable '{name}' is kind '{entry.kind}', expected '{expected_kind}'.")
            return x, entry.kind, name
    # Fallback: accept it, caller takes responsibility for correctness.
    return x, "unknown", getattr(x, "__name__", "<callable>")


def examples_of_registration():
    from dsl.registry_core import register, as_factory

    @register(
        kind="source",
        help="Stream items from a Python list.",
        tags=["list", "array", "demo", "beginner", "static"],
        aliases=["gen_list", "from_list"],
        param_schema={"items": {"type": "array",
                                "required": True, "example": ["a", "b"]}},
        io={"input": None, "output": "any"},
        example='generate("from_list", items=["a","b"])',
    )
    @as_factory
    def from_list(items):
        for x in items:
            yield x

    @register(
        kind="transform",
        help="Upper-case the message (coerced to string).",
        tags=["text", "uppercase", "string", "format"],
        aliases=["upper_case", "uppercase"],
        io={"input": "any", "output": "str"},
        example='transform("uppercase")',
    )
    def uppercase(msg):
        return str(msg).upper()

    @register(
        kind="sink",
        help="Print each message to the console.",
        tags=["print", "console", "debug", "log"],
        aliases=["to_console", "print"],
        param_schema={"prefix": {"type": "string", "default": ""}},
        io={"input": "any", "output": None},
        example='record("to_console", prefix="> ")',
    )
    def to_console(msg, *, prefix: str = ""):
        print(f"{prefix}{msg}")
