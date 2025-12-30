# dsl/graph.py
from __future__ import annotations
from typing import Callable
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple
import warnings
import inspect
import re

from dsl.core import Network
from dsl.blocks.source import Source
from dsl.blocks.sink import Sink
from dsl.blocks.transform import Transform
from dsl.blocks.fanout import Broadcast
from dsl.blocks.fanin import MergeAsynch

# Node = ("name", function)
NodePair = Tuple[str, Callable[..., Any]]

# Reserved prefixes created by the rewriter
_RESERVED_PREFIXES = ("broadcast_", "merge_")
# Optional: exact names you don't want users to reuse
_RESERVED_EXACT = {"broadcast", "merge", "source", "sink", "transform"}

# Match pairs like: (from_data, upper_case)
_PAIR_RE = re.compile(
    r"\(\s*([A-Za-z_][A-Za-z0-9_]*)\s*,\s*([A-Za-z_][A-Za-z0-9_]*)\s*\)")

# ---------------------------------------------------------
#                  NETWORK                          |
# ---------------------------------------------------------


def strip_quotes(s: str) -> str:
    s = s.strip()
    if len(s) >= 2 and s[0] == s[-1] and s[0] in ("'", '"'):
        return s[1:-1]
    return s


def _resolve_name(f: Callable, sep: str = "#") -> str:
    ''' Gives each node of the graph a unique name.
    A graph may have multiple nodes that are instances of the same class.
    Examples: obj_0 = Class_A(.., name="OBJ_0")), obj_1 = Class_A(.., name="OBJ_1")) 
    where obj_0.run and obj_1.run are nodes in the graph, and run(msg) is a method.
    Then the names of the nodes will be "OBJ_0#run" and "OBJ_1#run".
    Later, when building networks of networks we use full path names separated by dots
    as in "ParentNetwork.ChildNetwork.OBJ_0#run".

    '''
    # Bound method: obj.run
    self_obj = getattr(f, "__self__", None)
    if self_obj is not None:
        # f is a method of an object which is an instance of a class.
        # inst is the name of the object instance.
        inst = (
            getattr(self_obj, "name", None)
            or getattr(self_obj, "_name", None)
            or getattr(self_obj, "label", None)
            or getattr(self_obj, "_label", None)
        )
        if inst:
            # The name is the object instance name + separator + method name
            return f"{inst}{sep}{getattr(f, '__name__', 'call')}"
        return f"{self_obj.__class__.__name__}{sep}{getattr(f, '__name__', 'call')}"

    # Function on class / plain function
    qn = getattr(f, "__qualname__", None)
    # qn is a fully qualified name like ClassName.method_name
    if qn:
        return qn.replace(".", sep)

    nm = getattr(f, "__name__", None)
    return nm.replace(".", sep) if nm else repr(f)


def network(x: Iterable[Tuple[Callable, Callable]]) -> Graph:
    """
    x example: [(from_list, upper_case), (upper_case, to_results)]
    Returns:
      Graph(
        edges=[("from_list","upper_case"), ("upper_case","to_results")],
        nodes=[("from_list", from_list), ("upper_case", upper_case), ("to_results", to_results)]
      )
    """

    edges: List[Tuple[str, str]] = []
    seen_names: set[str] = set()
    ordered_funcs: List[Callable] = []

    for a, b in x:
        # Resolve readable, unique names for endpoints
        a_name = _resolve_name(a)
        b_name = _resolve_name(b)
        edges.append((a_name, b_name))

        # Collect unique functions in first-seen order
        for f, name in ((a, a_name), (b, b_name)):
            if name not in seen_names:
                seen_names.add(name)
                ordered_funcs.append(f)

    nodes = [(_resolve_name(f), f)
             for f in ordered_funcs]  # ("name", function)
    return Graph(edges=edges, nodes=nodes)


# ---------------------------------------------------------
#                  CLASS GRAPH                           |
# ---------------------------------------------------------


class Graph:
    """
    V2 Graph spec (single style):

      edges: list[tuple[str, str]]
          Edges as (u, v) pairs.

      nodes: list[tuple[str, callable]]
          Each node defined exactly once as ("name", fn).
          - Source  fn: () -> Iterator[Any]
          - Transform fn: (msg) -> Any
          - Sink     fn: (msg) -> None

    Roles are inferred by in/out-degree on the ORIGINAL edges:
      source    : indeg == 0 & outdeg >= 1
      sink      : outdeg == 0 & indeg >= 1
      transform : otherwise

    Rewriting:
      - If a node has >1 outgoing edges, insert a Broadcast node "broadcast_k".
      - If a node has >1 incoming edges, insert a Merge node "merge_j".
      - The final graph sends multi-fanouts via Broadcast and multi-fanins via MergeAsynch.

    Implementation notes:
      - We accept only the single style nodes=[("src", src), ("trn", trn), ...].
      - No params are passed via the graph; wrap config in closures.
    """

    def __init__(self, *, edges: Iterable[Tuple[str, str]], nodes: Iterable[NodePair]) -> None:
        # check types of parameters ----
        try:
            edge_list = list(edges)
        except TypeError:
            raise TypeError("edges must be an iterable of (u, v) pairs")

        try:
            node_list = list(nodes)
        except TypeError:
            raise TypeError(
                "nodes must be an iterable of ('name', function) pairs")

        # edges: (str, str)
        for i, e in enumerate(edge_list):
            if not (isinstance(e, (tuple, list)) and len(e) == 2):
                raise TypeError(f"edges[{i}] must be a (u, v) pair; got {e!r}")
            u, v = e
            if not (isinstance(u, str) and isinstance(v, str)):
                raise TypeError(
                    f"edges[{i}] must be (str, str); got ({type(u).__name__}, {type(v).__name__})"
                )
            if not u.strip() or not v.strip():
                raise ValueError(
                    f"edges[{i}] endpoints must be non-empty strings; got {e!r}")

        # nodes: ("name", callable)
        for i, item in enumerate(node_list):
            if not (isinstance(item, (tuple, list)) and len(item) == 2):
                raise TypeError(
                    f"nodes[{i}] must be ('name', function); got {item!r}, nodes ={node_list}")
            name, fn = item
            if not (isinstance(name, str) and name.strip()):
                raise TypeError(
                    f"nodes[{i}]: name must be a non-empty str; got {name!r}, nodes ={node_list}")
            if not callable(fn):
                raise TypeError(
                    f"nodes[{i}]: function must be callable; got {type(fn).__name__}, nodes ={node_list}")

        self.edges, self._fns = self._validate_and_normalize(
            edges, nodes)  # _fns: Dict[name, fn]
        self.nodes = self._fns.keys()
        self.network: Optional[Network] = None
        self.indeg: Dict[str, int] = {}
        self.outdeg: Dict[str, int] = {}

    # ---------- Validation / normalization ----------

    @staticmethod
    def _validate_and_normalize(
        edges_in: Iterable[Tuple[str, str]],
        nodes_in: Iterable[NodePair],
    ) -> Tuple[List[Tuple[str, str]], Dict[str, Callable[..., Any]]]:
        # Nodes: iterable of ("name", fn)

        try:
            pairs = list(nodes_in)
        except TypeError:
            raise TypeError(
                "nodes must be an iterable of ('name', function) pairs")

        fns: Dict[str, Callable[..., Any]] = {}
        for i, (name, fn) in enumerate(pairs):
            if not isinstance(name, str) or not name.strip():
                raise ValueError(f"Node #{i} has invalid name: {name!r}")
            if name in fns:
                raise ValueError(f"Duplicate node name '{name}' in nodes list")
            if not callable(fn):
                raise TypeError(
                    f"Node '{name}' must be a function/callable; got {type(fn).__name__}")

            # Reserved names/prefixes
            if any(name.startswith(pfx) for pfx in _RESERVED_PREFIXES):
                raise ValueError(
                    f"Node name '{name}' uses reserved prefix {_RESERVED_PREFIXES}")
            if name in _RESERVED_EXACT:
                raise ValueError(
                    f"Node name '{name}' is a reserved exact name: {_RESERVED_EXACT}")

            fns[name] = fn

        # Edges: list of (u, v)
        try:
            edge_list = list(edges_in)
        except TypeError:
            raise TypeError("edges must be an iterable of (u, v) pairs")

        norm_edges: List[Tuple[str, str]] = []
        for idx, e in enumerate(edge_list):
            if not (isinstance(e, (tuple, list)) and len(e) == 2):
                raise ValueError(
                    f"Edge #{idx} must be a pair (u, v); got {e!r}")
            u, v = e
            if not (isinstance(u, str) and u.strip() and isinstance(v, str) and v.strip()):
                raise ValueError(
                    f"Edge #{idx} endpoints must be non-empty strings; got {e!r}")
            norm_edges.append((u, v))

        # Cross-check membership
        referenced = {u for u, v in norm_edges} | {v for u, v in norm_edges}
        missing = sorted(n for n in referenced if n not in fns)
        if missing:
            hints = "\n".join(
                f"  - Add node ('{n}', fn) or remove/rename edges mentioning '{n}'"
                for n in missing
            )
            raise KeyError(
                f"Node(s) referenced by edges are missing: {missing}\nSuggestions:\n{hints}"
            )

        # De-dup edges (preserve first)
        seen = set()
        dedup_edges: List[Tuple[str, str]] = []
        dropped: List[Tuple[str, str]] = []
        for e in norm_edges:
            if e in seen:
                dropped.append(e)
                continue
            seen.add(e)
            dedup_edges.append(e)
        if dropped:
            warnings.warn(
                f"Removed {len(dropped)} duplicate edge(s): {dropped}", RuntimeWarning)

        # Warn on nodes not referenced
        unused = sorted(n for n in fns if n not in referenced)
        if unused:
            warnings.warn(
                f"{len(unused)} node(s) defined but not used in edges: {unused}\n"
                "Hint: add edges to connect them or remove the unused definitions.",
                RuntimeWarning,
            )

        return dedup_edges, fns

    @staticmethod
    def _validate_function_signature(name: str, role: str, fn: Callable[..., Any]) -> None:
        sig = inspect.signature(fn)
        params = list(sig.parameters.values())

        def required_positional_count() -> int:
            cnt = 0
            for p in params:
                if p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD) and p.default is p.empty:
                    cnt += 1
            return cnt

        req_pos = required_positional_count()

        if role == "source":
            # Should require no positional args (zero-arg callable)
            if req_pos > 0 and all(p.kind != p.VAR_POSITIONAL for p in params):
                raise TypeError(
                    f"Source node '{name}' should be a zero-argument function. "
                    f"Got signature: {fn.__name__}{sig}. "
                    "Hint: wrap configuration in a closure: "
                    "def src(): return from_list(items=..., key=...)"
                )
        else:
            # Transform/sink should accept at least one positional (the message), unless using *args
            if req_pos == 0 and not any(p.kind == p.VAR_POSITIONAL for p in params):
                raise TypeError(
                    f"Node '{name}' (role {role}) must accept a message parameter. "
                    f"Got signature: {fn.__name__}{sig}. Hint: def {name}(msg): ..."
                )

    # ---------- Public API ----------

    def compile(self) -> Network:
        roles = self._infer_roles()  # may rewrite self.edges and recompute indeg/outdeg
        blocks: Dict[str, Any] = {}

        # Build blocks for all role-bearing nodes, including injected broadcast/merge nodes
        for name, role in roles.items():
            if role in {"source", "transform", "sink"}:
                if name not in self._fns:
                    raise KeyError(
                        f"Node '{name}' referenced by edges but not provided in nodes list.")
                fn = self._fns[name]
                self._validate_function_signature(name, role, fn)
                if role == "source":
                    blocks[name] = Source(fn=fn, params={})
                elif role == "transform":
                    blocks[name] = Transform(fn=fn, params={})
                else:  # sink
                    blocks[name] = Sink(fn=fn, params={})

            elif role == "broadcast":
                blocks[name] = Broadcast(num_outports=self.outdeg[name])

            elif role == "merge":
                blocks[name] = MergeAsynch(num_inports=self.indeg[name])

            else:
                raise ValueError(f"Unknown role '{role}' for node '{name}'")

        # Build connections, handling multi-port broadcast/merge
        n_connected: Dict[str, int] = {n: 0 for n in roles.keys()}
        connections: List[Tuple[str, str, str, str]] = []

        for u, v in self.edges:
            ru, rv = roles[u], roles[v]

            if ru != "broadcast" and rv != "merge":
                # single out → single in
                connections.append((u, "out", v, "in"))

            elif ru == "broadcast" and rv != "merge":
                # broadcast has numbered outports
                out_i = n_connected[u]
                connections.append((u, f"out_{out_i}", v, "in"))
                n_connected[u] += 1

            elif ru != "broadcast" and rv == "merge":
                # merge has numbered inports
                in_i = n_connected[v]
                connections.append((u, "out", v, f"in_{in_i}"))
                n_connected[v] += 1

            else:
                # broadcast → merge
                out_i = n_connected[u]
                in_i = n_connected[v]
                connections.append((u, f"out_{out_i}", v, f"in_{in_i}"))
                n_connected[u] += 1
                n_connected[v] += 1

        self.network = Network(blocks=blocks, connections=connections)
        return self.network

    def compile_and_run(self) -> None:
        net = self.network or self.compile()
        net.compile_and_run()

    def run_network(self, *args, **kwargs):
        """Run the network (alias for compile_and_run)."""
        return self.compile_and_run(*args, **kwargs)

    # ---------- Role inference + rewrites ----------

    def _infer_roles(self) -> Dict[str, str]:
        # Snapshot original edges for degree computation
        original_edges = list(self.edges)

        names = set(self.nodes)
        for u, v in original_edges:
            names.add(u)
            names.add(v)
        names = sorted(names)  # determinism

        # Degrees on original graph
        indeg0 = {n: 0 for n in names}
        outdeg0 = {n: 0 for n in names}
        for u, v in original_edges:
            outdeg0[u] += 1
            indeg0[v] += 1

        # Initial roles (on original)
        roles: Dict[str, str] = {}
        for n in names:
            if indeg0[n] == 0 and outdeg0[n] == 0:
                raise ValueError(f"node '{n}' has no incident edges.")
            if indeg0[n] == 0:
                roles[n] = "source"
            elif outdeg0[n] == 0:
                roles[n] = "sink"
            else:
                roles[n] = "transform"

        # Rewire: fan-out via broadcast, fan-in via merge
        # new_edges will be modified but original_edges stays unchanged.
        new_edges = list(original_edges)
        bcount = 0
        mcount = 0

        # Fan-out: for any node with >1 outgoing (in new_edges)
        for n in names:
            outs = [v for (u, v) in new_edges if u == n]
            if len(outs) > 1:
                bname = f"broadcast_{bcount}"
                while bname in roles or bname in self._fns:
                    bcount += 1
                    bname = f"broadcast_{bcount}"
                bcount += 1
                roles[bname] = "broadcast"
                # remove (n, outs) then add (n, bname) + (bname, v)
                new_edges = [(u, v)
                             for (u, v) in new_edges if not (u == n and v in outs)]
                new_edges.append((n, bname))
                new_edges.extend((bname, v) for v in outs)

        # Fan-in: for any node with >1 incoming (in new_edges)
        for n in names:
            ins = [u for (u, v) in new_edges if v == n]
            if len(ins) > 1:
                mname = f"merge_{mcount}"
                while mname in roles or mname in self._fns:
                    mcount += 1
                    mname = f"merge_{mcount}"
                mcount += 1
                roles[mname] = "merge"
                # remove (ins, n) then add (mname, n) + (u, mname)
                new_edges = [(u, v)
                             for (u, v) in new_edges if not (u in ins and v == n)]
                new_edges.append((mname, n))
                new_edges.extend((u, mname) for u in ins)

        # Commit rewritten edges
        self.edges = new_edges

        # Recompute degrees on the FINAL graph for port counts
        final_names = set(self._fns.keys()) | {u for u, v in self.edges} | {
            v for u, v in self.edges}
        self.indeg = {n: 0 for n in final_names}
        self.outdeg = {n: 0 for n in final_names}
        for u, v in self.edges:
            self.outdeg[u] += 1
            self.indeg[v] += 1

        # Check
        for n in final_names:
            if n not in roles:
                # Single-degree nodes may appear only if injected; infer from final degrees
                if self.indeg[n] > 1:
                    assert (roles[n] == "merge") and (self.outdeg[n] == 1)
                elif self.outdeg[n] > 1:
                    assert (roles[n] == "broadcast") and (self.indeg[n] == 1)
                elif self.indeg[n] == 0:
                    assert (roles[n] == "source") and (self.outdeg[n] == 1)
                elif self.outdeg[n] == 0:
                    assert (roles[n] == "sink") and (self.indeg[n] == 1)
                else:
                    assert (roles[n] == "transform") and (
                        self.indeg == 1) and (self.outdeg == 1)

        return roles
