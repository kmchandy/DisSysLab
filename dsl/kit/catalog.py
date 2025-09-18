# dsl/kit/catalog.py
from __future__ import annotations

from dataclasses import dataclass
from functools import wraps, partial
from typing import Any, Callable, Dict, Iterator, Optional

# -------------------------------------------------------------------
# Public Catalog (whitelist) — single source of truth for functions
# -------------------------------------------------------------------

CATALOG_VERSION: str = "kit.curated@0.1.0"


@dataclass(frozen=True)
class CatalogEntry:
    kind: str                       # "source" | "transform" | "sink"
    # live callable (see kind-specific contract below)
    callable: Callable[..., Any]
    help: str = ""
    # optional, light hints for validation/UI
    param_schema: Dict[str, Any] = None
    # optional, e.g., {"out": ["left","right"]}
    default_shape: Dict[str, Any] = None
    # optional student-facing alias (e.g., "FromList")
    kit_name: Optional[str] = None


# name (str) -> CatalogEntry
CATALOG: Dict[str, CatalogEntry] = {}


def register(
    *,
    kind: str,                 # "source" | "transform" | "sink"
    kit_name: str | None = None,
    help: str = "",
    param_schema: Dict[str, Any] | None = None,
    default_shape: Dict[str, Any] | None = None,
):
    """
    Decorator to register a function in the CATALOG with metadata.

    Contracts by kind:
      - source:    the registered callable MUST be a *factory factory*:
                   fn(**params) -> zero-arg generator factory -> iterator
                   (Use @as_factory on your generator to get this shape.)
      - transform: the registered callable is a pure mapping:
                   fn(msg: Any, **params) -> Any
      - sink:      the registered callable is a recorder:
                   fn(msg: Any, **params) -> None
    """
    if kind not in {"source", "transform", "sink"}:
        raise ValueError(
            f"register(kind=...) must be 'source'|'transform'|'sink', got {kind!r}")

    def deco(fn: Callable[..., Any]):
        entry = CatalogEntry(
            kind=kind,
            callable=fn,
            help=help,
            param_schema=param_schema or {},
            default_shape=default_shape or {},
            kit_name=kit_name,
        )
        CATALOG[fn.__name__] = entry
        return fn

    return deco


def as_factory(f: Callable[..., Iterator[Any]]) -> Callable[..., Callable[[], Iterator[Any]]]:
    """
    Wrap a parameterized generator function so calling it with params
    returns a ZERO-ARG factory, which later returns the iterator.

    Usage:
        @as_factory
        def gen_list(items) -> Iterator[Any]:
            for x in items:
                yield x

        factory = gen_list(items=[1,2,3])  # zero-arg factory
        it = factory()                      # iterator -> yields 1,2,3
    """
    @wraps(f)
    def wrapper(*args, **kwargs) -> Callable[[], Iterator[Any]]:
        def _factory() -> Iterator[Any]:
            # Important: return the iterator produced by f(...)
            return f(*args, **kwargs)
        return _factory
    return wrapper


# -------------------------------------------------------------------
# Binding resolution helpers (for your loader)
# -------------------------------------------------------------------

def resolve_binding(ref: str, fn_name: str, params: Dict[str, Any]) -> CatalogEntry:
    """
    Look up a fn_name in the CATALOG and return the CatalogEntry.
    Raise a friendly error if unknown.
    """
    entry = CATALOG.get(fn_name)
    if entry is None:
        # Very small "did you mean" helper
        suggestions = ", ".join(sorted(CATALOG.keys()))
        raise KeyError(f"Unknown function '{fn_name}' for ref '{ref}'. "
                       f"Known functions: {suggestions}")
    # (Optional) Here you could validate params using entry.param_schema
    return entry


# -------------------------------------------------------------------
# Optional: auto-create student-friendly kit classes from catalog
# Call this from dsl/kit/__init__.py to expose FromList, UpperCase, etc.
# -------------------------------------------------------------------

def _make_source_class(name: str, factory_factory: Callable[..., Callable[[], Iterator[Any]]]):
    # Delayed import to avoid cycles
    from dsl.block_lib.sources.source import Source

    class _AutoSource(Source):  # type: ignore[misc]
        def __init__(self, **params):
            super().__init__(generator_fn=factory_factory(**params))

    _AutoSource.__name__ = name
    _AutoSource.__qualname__ = name
    _AutoSource.__doc__ = f"Auto-generated Source wrapper for `{factory_factory.__name__}`"
    return _AutoSource


def _make_transform_class(name: str, func: Callable[..., Any]):
    from dsl.block_lib.transforms.transform import Transform

    class _AutoTransform(Transform):  # type: ignore[misc]
        def __init__(self, **params):
            # Wrap func(msg, **params) into a single-arg callable for Transform
            def _call(msg):
                return func(msg, **params)
            super().__init__(func=_call, name=name)

    _AutoTransform.__name__ = name
    _AutoTransform.__qualname__ = name
    _AutoTransform.__doc__ = f"Auto-generated Transform wrapper for `{func.__name__}`"
    return _AutoTransform


def _make_sink_class(name: str, recorder: Callable[..., None]):
    from dsl.block_lib.sinks.sink import Sink

    class _AutoSink(Sink):  # type: ignore[misc]
        def __init__(self, **params):
            # Wrap record_fn(msg, **params) into a single-arg recorder
            def _record(msg):
                return recorder(msg, **params)
            super().__init__(record_fn=_record, name=name)

    _AutoSink.__name__ = name
    _AutoSink.__qualname__ = name
    _AutoSink.__doc__ = f"Auto-generated Sink wrapper for `{recorder.__name__}`"
    return _AutoSink


def build_kit_aliases() -> Dict[str, Any]:
    """
    Create student-friendly classes (FromList, UpperCase, ToConsole, etc.)
    for all catalog entries that specified kit_name.

    Returns a dict mapping kit_name -> class, ready to inject into `dsl.kit` globals.
    """
    aliases: Dict[str, Any] = {}
    for fn_name, entry in CATALOG.items():
        kit_name = entry.kit_name
        if not kit_name:
            continue
        if entry.kind == "source":
            aliases[kit_name] = _make_source_class(
                kit_name, entry.callable)  # type: ignore[arg-type]
        elif entry.kind == "transform":
            aliases[kit_name] = _make_transform_class(kit_name, entry.callable)
        elif entry.kind == "sink":
            aliases[kit_name] = _make_sink_class(kit_name, entry.callable)
    return aliases


# -------------------------------------------------------------------
# Starter entries (minimal but useful). Add more as you go.
# Authors: write ONE function + @register (and @as_factory for sources).
# -------------------------------------------------------------------

@register(
    kind="source",
    kit_name="FromList",
    help="Stream items from a Python list.",
    param_schema={"items": {"type": "array",
                            "description": "Items to emit in order."}},
)
@as_factory
def gen_list(items) -> Iterator[Any]:
    for x in items:
        yield x


@register(
    kind="transform",
    kit_name="UpperCase",
    help="Upper-case the message (coerced to string).",
)
def upper_case(msg: Any) -> Any:
    return str(msg).upper()


@register(
    kind="sink",
    kit_name="ToConsole",
    help="Print each message. Optional 'prefix' param.",
    param_schema={"prefix": {"type": "string", "default": ""}},
)
def to_console(msg: Any, *, prefix: str = "") -> None:
    print(f"{prefix}{msg}")
