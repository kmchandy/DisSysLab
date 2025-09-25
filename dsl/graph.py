# dsl/graph.py
from __future__ import annotations
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple, Union
import warnings
import importlib

from dsl.core import Network
from dsl.blocks.source import Source
from dsl.blocks.sink import Sink
from dsl.blocks.transform import Transform
from dsl.blocks.fanout import Broadcast
from dsl.blocks.fanin import MergeAsynch

NodeSpec = Union[
    Tuple[Callable[..., Any], Dict[str, Any]],
]

_RESERVED_PREFIXES = ("broadcast_", "merge_")
_RESERVED_NAMES = ("broadcast", "merge", "source", "sink", "transform")


class Graph:
    """
      - edges = [("src", "snk"), ...]
      - nodes = {
            "src": (from_list, {"items": [...]}) 
            "snk": (to_list,   {"target": results})
        }

    Roles are inferred by in/out-degree:
      source  : indeg==0 & outdeg>=1
      sink    : outdeg==0 & indeg>=1
      transform: otherwise
      add broadcast nodes if outdeg > 1

    Function shapes:
      Source    fn(**params) -> Iterator
      Transform fn(msg, **params) -> Any
      Sink      fn(msg, **params) -> None
      Broadcast no fn -> None
    """

    def __init__(self, *, edges: Iterable[Tuple[str, str]], nodes: Dict[str, NodeSpec]) -> None:
        self.edges, self.nodes = self._validate_and_normalize(edges, nodes)
        # self.network is the network created by compile()
        self.network: Optional[Network] = None
        # The in-degree and out-degree of nodes of the graph.
        self.indeg: Dict[str, int] = {}
        self.outdeg: Dict[str, int] = {}

    @staticmethod
    def _validate_and_normalize(
        edges_in: Iterable[Tuple[str, str]],
        nodes_in: Dict[str, NodeSpec],
    ) -> Tuple[List[Tuple[str, str]], Dict[str, NodeSpec]]:
        # ---- nodes ----
        if not isinstance(nodes_in, dict) or not nodes_in:
            raise TypeError(
                "nodes must be a non-empty dict mapping 'name' -> (callable, params_dict).\n"
                "Hint: nodes = {'src': (from_list, {'items': [...]})}"
            )

        norm_nodes: Dict[str, NodeSpec] = {}
        for name, spec in nodes_in.items():
            if not isinstance(name, str) or not name.strip():
                raise ValueError(
                    f"Node names must be non-empty strings; got {name!r}")

            for prefix in _RESERVED_PREFIXES:
                if name.startswith(prefix):
                    raise ValueError(
                        f"Node name {name!r} collides with reserved prefix {prefix!r} "
                        "used internally (e.g., broadcast nodes). Hint: rename your node."
                    )
            for _name in _RESERVED_NAMES:
                if name == _name:
                    raise ValueError(
                        f"Node name {name!r} is a reserved word"
                    )

            # Must be exactly (callable, dict)
            if not isinstance(spec, tuple):
                if callable(spec):
                    raise TypeError(
                        f"Node {name!r} must be given as (callable, params_dict).\n"
                        f"Hint: nodes['{name}'] = ({getattr(spec, '__name__', '<fn>')}, {{}})"
                    )
                if isinstance(spec, dict) and ("fn" in spec or "params" in spec):
                    raise TypeError(
                        f"Node {name!r} looks like a dict spec, but v2 expects a tuple.\n"
                        f"Use: nodes['{name}'] = (fn, {{...}})"
                    )
                raise TypeError(
                    f"Node {name!r} must be (callable, params_dict); got {type(spec).__name__}"
                )

            if len(spec) != 2:
                raise TypeError(
                    f"Node {name!r} tuple must be (callable, params_dict); got length {len(spec)}")

            fn, params = spec
            if not callable(fn):
                raise TypeError(
                    f"Node {name!r}: first element must be callable; got {type(fn).__name__}")
            if not isinstance(params, dict):
                raise TypeError(
                    f"Node {name!r}: second element must be a dict of params (use {{}} if none); got {type(params).__name__}"
                )

            norm_nodes[name] = (fn, dict(params))

        # ---- edges ----
        try:
            edge_list = list(edges_in)
        except TypeError:
            raise TypeError("edges must be an iterable of (u, v) pairs")

        norm_edges: List[Tuple[str, str]] = []
        for i, e in enumerate(edge_list):
            if not (isinstance(e, (tuple, list)) and len(e) == 2):
                raise ValueError(f"Edge #{i} must be a pair (u, v); got {e!r}")
            u, v = e
            if not (isinstance(u, str) and isinstance(v, str) and u.strip() and v.strip()):
                raise ValueError(
                    f"Edge #{i} endpoints must be non-empty strings; got {e!r}")
            for prefix in _RESERVED_PREFIXES:
                if u.startswith(prefix) or v.startswith(prefix):
                    raise ValueError(
                        f"Edge {e!r} uses reserved prefix {prefix!r}. Hint: rename node(s) not to start with '{prefix}'."
                    )
            norm_edges.append((u, v))

        # ---- cross-check membership ----
        referenced = {u for u, v in norm_edges} | {v for u, v in norm_edges}
        missing = sorted(n for n in referenced if n not in norm_nodes)
        if missing:
            hints = "\n".join(
                f"  - Add nodes'{n}' = (fn, {{}})  or remove edges mentioning '{n}'"
                for n in missing
            )
            raise KeyError(
                f"nodes {missing} referenced by edges are missing from the list of nodes."
                f"Suggestions:"
                f"{hints}"
            )

        # ---- duplicates & unused ----
        # De-duplicate edges, preserving order; warn if any dropped
        seen = set()
        dedup_edges = []
        dropped = []
        for e in norm_edges:
            if e in seen:
                dropped.append(e)
                continue
            seen.add(e)
            dedup_edges.append(e)
        if dropped:
            warnings.warn(
                f"Removed {len(dropped)} duplicate edge(s): {dropped}", RuntimeWarning)

        # Warn on nodes defined but not referenced by any edge
        unused = sorted(n for n in norm_nodes.keys() if n not in referenced)
        if unused:
            warnings.warn(
                f"{len(unused)} node(s) defined but not used in edges: {unused}\n"
                "Hint: add edges to connect them or remove the unused definitions.",
                RuntimeWarning,
            )

        return dedup_edges, norm_nodes

    # ---------- Public API ----------

    def compile(self) -> Network:
        roles = self._infer_roles()
        blocks: Dict[str, Any] = {}

        # ---------------------------------
        # Make blocks
        # ---------------------------------

        for name, spec in self.nodes.items():
            # name is a node in the graph
            role = roles.get(name)
            # Every role other than broadcast and merge must have a spec.
            # broadcast and merge roles have no spec.
            if spec:
                fn, params = spec

            if role == "source":
                block = Source(fn=fn, params=params)
            elif role == "transform":
                block = Transform(fn=fn, params=params)
            elif role == "sink":
                block = Sink(fn=fn, params=params)
            elif role == "broadcast":
                block = Broadcast(num_outports=self.outdeg[name])
            elif role == "merge":
                block = MergeAsynch(num_inports=self.indeg[name])
            else:
                raise ValueError(f"could not infer role for node '{name}'")

            blocks[name] = block

        # ---------------------------------
        # Make connections
        # ---------------------------------
        n_connected = {name: 0 for name in self.nodes.keys()}
        connections = []

        for (u, v) in self.edges:
            role_u, role_v = roles.get(u), roles.get(v)
            if (role_u != "broadcast" and
                    role_v != "merge"):
                # u has single output, v has single input
                connections.append((u, "out", v, "in"))

            elif (role_u == "broadcast" and
                  role_v != "merge"):
                outport_number = n_connected[u]
                outport = f"out_{outport_number}"
                connections.append((u, outport, v, "in"))
                n_connected[u] += 1

            elif (role_u != "broadcast" and
                  role_v == "merge"):
                inport_number = n_connected[v]
                inport = f"in_{inport_number}"
                connections.append((u, "out", v, inport))
                n_connected[v] += 1

            else:
                # role_u == "broadcast" and role_v == "merge"
                outport_number = n_connected[u]
                outport = f"out_{outport_number}"
                inport_number = n_connected[v]
                inport = f"in_{inport_number}"
                connections.append((u, outport, v, inport))
                n_connected[u] += 1
                n_connected[v] += 1

        self.network = Network(blocks=blocks, connections=connections)

    def compile_and_run(self) -> None:
        self.compile()  # create self.network
        self.network.compile_and_run()

    # ---------- Helpers ----------
    def _infer_roles(self) -> Dict[str, str]:
        names = set(self.nodes.keys())

        # Determine set (called names) of nodes.
        for (u, v) in self.edges:
            names.add(u)
            names.add(v)

        # Compute in-degree and out_degree of nodes of the graph.
        self.indeg = {n: 0 for n in names}
        self.outdeg = {n: 0 for n in names}
        for (u, v) in self.edges:
            self.outdeg[u] += 1
            self.indeg[v] += 1

        # --------------------------------------------------
        # Add merge nodes at fanin points
        # If a node y has multiple input edges (x, y) then
        # create a new merge node z, and create edges (x, z)
        # (z, y), and remove edges (x, y).
        # So, all fanin are to merge nodes.

        # Add broadcast nodes at fanout points
        # If a node y has multiple output edges (y, x) then
        # create a new broadcast node z, and create edges (z, x)
        # (y, z), and remove edges (y, x).
        # So, all fanout are to broadcast nodes.

        k = 0  # number of broadcast nodes added to graph
        j = 0  # number of merge nodes added to graph
        # Give unique names to broadcast and merge nodes.
        # The k-th broadcast node is "broadcast_k" and
        # the j-th merge node is "merge_j"
        roles: Dict[str, str] = {}
        for n in names:
            if self.indeg[n] == 0 and self.outdeg[n] == 0:
                raise ValueError(f"node '{n}' has no incident edges.")
            if self.indeg[n] == 0:
                roles[n] = "source"
            elif self.outdeg[n] == 0:
                roles[n] = "sink"
            else:
                # self.indeg[n] > 0 and self.outdeg[n] > 0
                roles[n] = "transform"
            # ---------------------
            # ADD BROADCAST NODE
            # ---------------------
            if self.outdeg[n] > 1:
                # Add a broadcast node which has outdeg[n] outports
                # Node n connects only to this broadcast node.
                # The outputs of this broadcast connect to outputs
                # of node n in the initial graph.

                # Remove edges from node n
                outs = [v for (u, v) in self.edges if u == n]
                self.edges = [(u, v) for (u, v) in self.edges if u != n]

                # Add a broadcast node called f"broadcast_{k}"
                # broadcast node has single inport and len(outs) outports.
                # add broadcast node after node n
                bname = f"broadcast_{k}"
                roles[bname] = "broadcast"
                k += 1
                # add single edge from n to the broadcast.
                self.edges.append((n, bname))
                # Add edges from the broadcast to original nodes from node n.
                self.edges.extend((bname, v) for v in outs)
                self.indeg[bname] = 1
                self.outdeg[bname] = len(outs)
                # Add the broadcast node to the nodes of the graph
                # A broadcast node has a None spec.
                self.nodes[bname] = None

            # ---------------------
            # ADD MERGE NODE
            # ---------------------
            if self.indeg[n] > 1:
                # Add a merge node which has indeg[n] outports
                # The inputs of this merge are the inputs
                # of node n in the initial graph.

                # Remove edges to node n
                ins = [u for (u, v) in self.edges if v == n]
                self.edges = [(u, v) for (u, v) in self.edges if v != n]

                # Add a merge node called f"merge_{j}"
                # merge node has single outport and len(ins) inports.
                # add the merge node with an edge from merge node to node n
                bname = f"merge_{j}"
                roles[bname] = "merge"
                j += 1
                # add single edge to n from the merge.
                self.edges.append((bname, n))
                # Add edges to the merge from original nodes to node n.
                self.edges.extend((v, bname) for v in ins)
                self.indeg[bname] = len(ins)
                self.outdeg[bname] = 1
                # Add the merge node to the nodes of the graph
                # A merge node has a None spec.
                self.nodes[bname] = None
        # assert:
        # for all nodes n of the graph:
        #   if outdeg[n] == 0 and indeg[n] == 1 then roles[n] == "sink"
        #   if outdeg[n] == 1 and indeg[n] == 0 then roles[n] == "source"
        #   if outdeg[n] == 1 and indeg[n] ==1 then roles[n] == "transform"
        #   if outdeg[n] > 1 then indeg[n] ==1 and roles[n] == "broadcast"
        #   if indeg[n] > 1 then outdeg[n] == 1 and roles[n] == "merge"
        return roles
