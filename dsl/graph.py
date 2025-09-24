# dsl/graph.py
from __future__ import annotations
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple, Union
import importlib

from dsl.core import Network
from dsl.blocks.source import Source
from dsl.blocks.sink import Sink
# Transform imported lazily only if needed.

# Supported node specs:
#   • callable
#   • (callable, {params})
#   • "module:qualname"
#   • ("module:qualname", {params})
NodeSpec = Union[
    Callable[..., Any],
    Tuple[Callable[..., Any], Dict[str, Any]],
    str,
    Tuple[str, Dict[str, Any]],
]

_ALIAS = {"ops": "dsl.ops"}  # allow short IDs like "ops:to_list"


def _resolve_id(id_str: str) -> Any:
    mod_name, qual = id_str.split(":", 1)
    mod_name = _ALIAS.get(mod_name, mod_name)
    parts = qual.split(".")
    module_path = mod_name + \
        ("" if len(parts) == 1 else "." + ".".join(parts[:-1]))
    try:
        mod = importlib.import_module(module_path)
        return getattr(mod, parts[-1])
    except Exception:
        mod = importlib.import_module(mod_name)
        obj = mod
        for part in parts:
            obj = getattr(obj, part)
        return obj


class Graph:
    """
    Minimal Python DSL mirroring the YAML shape:
      - edges = [("src", "snk"), ...]
      - nodes = {
            "src": (from_list, {"items": [...]})  # or just from_list
            "snk": (to_list,   {"target": results})
        }

    Roles are inferred by in/out-degree:
      source  : indeg==0 & outdeg>=1
      sink    : outdeg==0 & indeg>=1
      transform: otherwise

    Function shapes (frozen in v2):
      Source    fn(**params) -> Iterator
      Transform fn(msg, **params) -> Any
      Sink      fn(msg, **params) -> None
    """

    def __init__(self, *, edges: Iterable[Tuple[str, str]], nodes: Dict[str, NodeSpec]) -> None:
        self.edges: List[Tuple[str, str]] = list(edges)
        self.nodes: Dict[str, NodeSpec] = dict(nodes)

    # ---------- Public API ----------
    def compile(self) -> Network:
        roles = self._infer_roles()
        blocks: Dict[str, Any] = {}

        needs_transform = any(r == "transform" for r in roles.values())
        Transform = None
        if needs_transform:
            from dsl.blocks.transform import Transform as _T
            Transform = _T

        for name, spec in self.nodes.items():
            role = roles.get(name)
            if role is None:
                raise ValueError(
                    f"Node '{name}' has no incident edge; cannot infer role.")
            fn, params = self._as_fn_params(spec)

            if role == "source":
                block = Source(fn=fn, params=params)
            elif role == "transform":
                if Transform is None:
                    raise RuntimeError(
                        "Transform block required but not available.")
                block = Transform(fn=fn, params=params)
            else:
                block = Sink(fn=fn, params=params)

            blocks[name] = block

        connections = [(u, "out", v, "in") for (u, v) in self.edges]
        return Network(blocks=blocks, connections=connections)

    def compile_and_run(self) -> None:
        net = self.compile()
        if hasattr(net, "compile_and_run"):
            net.compile_and_run()
        else:
            if hasattr(net, "compile"):
                net.compile()
            if hasattr(net, "run"):
                net.run()

    # ---------- Helpers ----------
    def _infer_roles(self) -> Dict[str, str]:
        names = set(self.nodes.keys())
        for u, v in self.edges:
            names.add(u)
            names.add(v)

        indeg = {n: 0 for n in names}
        outdeg = {n: 0 for n in names}
        for u, v in self.edges:
            outdeg[u] += 1
            indeg[v] += 1

        roles: Dict[str, str] = {}
        for n in names:
            if indeg[n] == 0 and outdeg[n] >= 1:
                roles[n] = "source"
            elif outdeg[n] == 0 and indeg[n] >= 1:
                roles[n] = "sink"
            else:
                roles[n] = "transform"
        return roles

    def _as_fn_params(self, spec: NodeSpec) -> Tuple[Callable[..., Any], Dict[str, Any]]:
        # (callable, params)
        if isinstance(spec, tuple) and callable(spec[0]):
            fn, params = spec
            return fn, dict(params)
        # callable
        if callable(spec):
            return spec, {}
        # ("module:qual", params)
        if isinstance(spec, tuple) and isinstance(spec[0], str):
            fn = _resolve_id(spec[0])
            return fn, dict(spec[1])
        # "module:qual"
        if isinstance(spec, str):
            fn = _resolve_id(spec)
            return fn, {}
        raise TypeError(f"Unsupported node spec: {type(spec).__name__}")
