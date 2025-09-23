# dsl/kit/catalog_bootstrap.py
from __future__ import annotations
from pathlib import Path
from types import SimpleNamespace

from dsl.registry import RegistryMap
from dsl.registry_utils import register_functions_in_file, register_functions_in_module

# The one-and-only global registry
REGISTRY: RegistryMap = {}


def _bootstrap_registry() -> None:
    # Resolve <repo>/dsl/ops/sources/lists.py
    src_lists_path = Path(__file__).parents[1] / "ops" / "sources" / "lists.py"
    register_functions_in_file(
        registry=REGISTRY,
        path=src_lists_path,
        kind="source",
        namespace="dsl.ops.sources.lists",
    )

    # Optionally register sinks (if you have dsl/ops/sinks/lists.py)
    try:
        sink_lists_path = Path(
            __file__).parents[1] / "ops" / "sinks" / "lists.py"
        register_functions_in_file(
            registry=REGISTRY,
            path=sink_lists_path,
            kind="sink",
            namespace="dsl.ops.sinks.lists",
        )
    except FileNotFoundError:
        pass  # fine for now

    # Optional stdlib string transforms
    str_funcs = SimpleNamespace(
        upper=str.upper, lower=str.lower, strip=str.strip,
        lstrip=str.lstrip, rstrip=str.rstrip, replace=str.replace,
    )
    register_functions_in_module(
        registry=REGISTRY,
        module=str_funcs,
        kind="transform",
        namespace="py.str",
    )


# Build on import
_bootstrap_registry()


def build_registry() -> RegistryMap:
    """Return the populated registry (ids -> (Registration, callable))."""
    return REGISTRY
