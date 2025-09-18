# dsl/kit/catalog.py  (concept sketch)

from functools import wraps
from typing import Any, Callable, Dict, Iterator

# The whitelist catalog the loader will use: name -> metadata
CATALOG: Dict[str, Dict[str, Any]] = {}


def register(
    *,
    kind: str,                 # "source" | "transform" | "sink"
    # optional student-facing alias (e.g., "FromList")
    kit_name: str | None = None,
    help: str = "",
    # optional hints for validation/UI
    param_schema: Dict[str, Any] | None = None,
    # optional (e.g., {"out": ["left","right"]})
    default_shape: Dict[str, Any] | None = None
):
    """Attach metadata and add the function to the CATALOG."""
    def deco(fn: Callable[..., Any]):
        CATALOG[fn.__name__] = {
            "kind": kind,
            "callable": fn,          # the live callable
            "help": help,
            "param_schema": param_schema or {},
            "default_shape": default_shape or {},
            "kit_name": kit_name,
        }
        return fn
    return deco


def as_factory(f: Callable[..., Iterator[Any]]) -> Callable[..., Callable[[], Iterator[Any]]]:
    """Wrap a generator function so calling it with params returns a zero-arg factory."""
    @wraps(f)
    def wrapper(*args, **kwargs) -> Callable[[], Iterator[Any]]:
        def _gen() -> Iterator[Any]:
            # f(*args, **kwargs) already returns an iterator
            return f(*args, **kwargs)
        return _gen
    return wrapper

# ---------- Examples authors would write ----------


@register(
    kind="source",
    kit_name="FromList",
    help="Stream items from a Python list.",
    param_schema={"items": {"type": "array"}}
)
@as_factory
def gen_list(items) -> Iterator[Any]:
    for x in items:
        yield x


@register(
    kind="transform",
    kit_name="UpperCase",
    help="Convert strings to uppercase."
)
def upper_case(msg: Any) -> Any:
    return str(msg).upper()


@register(
    kind="sink",
    kit_name="ToConsole",
    help="Print each message.",
    param_schema={"prefix": {"type": "string", "default": ""}}
)
def to_console(msg: Any, *, prefix: str = "") -> None:
    print(f"{prefix}{msg}")

# ---------- How the loader will use it (concept) ----------
# bindings["block_0"] = {"fn": "gen_list", "params": {"items": ["a","b"]}}
# entry   = CATALOG["gen_list"]
# factory = entry["callable"]                 # <- the decorated function
# gen_fn  = factory(**{"items": ["a","b"]})   # <- zero-arg generator factory
# Source(generator_fn=gen_fn)                 # role decides the wrapper
