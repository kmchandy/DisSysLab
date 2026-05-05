"""
Layer 5 — turn an OfficeSpec + role library into a runtime Network.

The compiler is intentionally small. Most of the heavy lifting was
done in earlier layers:

* The **parser** (Layer 4) gave us a normalised ``OfficeSpec`` whose
  ``agents`` are uniform ``RoleRef``s and whose connection statements
  already know which ends sit on the office boundary.
* The **library** (Layer 3) tells us how to materialise each role —
  whether it is a leaf ``Agent`` or a sub-office on disk.
* The **runtime** ``dissyslab.network.Network`` validates the final
  graph in its constructor (port existence, "external" wiring,
  unique block names) and flattens nested networks at run time.

Everything Layer 5 does fits in a single tree-walk:

1. Build a ``blocks`` dict: one entry per source, sink, leaf agent,
   or sub-office. Sub-offices recurse via a fresh ``compile_office``
   call on disk; their library is loaded from their own
   ``roles_lib/``.
2. Translate each ``ConnectionStmt`` into one or more 4-tuples,
   converting the user-written semantic outport names
   (``"briefing"``, ``"discard"``, …) into the runtime's indexed
   outport names (``"out_0"``, ``"out_1"``, …) for ``Role``-shaped
   agents, and into ``"out_"`` for sources. Destination side is
   already in runtime form (parser put the implicit inport in for
   bare names; sub-office and external destinations carry their
   declared port names verbatim).
3. Hand the resulting ``blocks`` and ``connections`` to
   ``Network(...)``. The constructor's ``check()`` raises if any
   wiring is wrong.

What Layer 5 does NOT do
========================

* No flattening — the runtime's ``_flatten_networks`` does it.
* No fanout/fanin insertion — the runtime's ``_insert_fanout_fanin``
  does it.
* No port-shape consistency check — ``Network.check()`` does it on
  every parent constructor call.
* No code that knows the difference between a leaf agent and a
  sub-office at run time. Both are just blocks in a dict.

Sub-office libraries
====================

Each office is its own library boundary. A parent office's
``compile_office(parent_dir, library=...)`` override applies only to
the parent. When the compiler descends into a sub-office it makes a
fresh ``compile_office(child_dir)`` call with no ``library=``
argument, so the child loads its own ``roles_lib/`` (and its
``roles/`` fallback). That keeps offices self-contained and lets
the same office work both as a top-level program and as a sub-office.

Inline ``office at <path>`` sugar
==================================

If a parent's office.md says ``X is an office at ../news_monitor.``
the parser captures the path on the ``RoleRef``. At compile time:

* If the library has an ``OfficeRoleEntry`` for that role name, it
  wins (explicit beats sugar).
* Otherwise the compiler descends into the captured path and emits
  a warning recommending an explicit library entry.

That keeps the v1 gallery's ``Offices: news_monitor is path/...``
form working while we transition to library-based discovery.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

from dissyslab.core import Agent
from dissyslab.network import Network
from dissyslab.blocks.source import Source
from dissyslab.blocks.sink import Sink

from dissyslab.office_v2._internals import (
    CompileError,
    CompileWarning,
    _BlockTable,
    _load_office_library,
    _resolve_subpath,
    _runtime_inport,
    _runtime_outport,
)
from dissyslab.office_v2.library import (
    AgentRoleEntry,
    Library,
    OfficeRoleEntry,
)
from dissyslab.office_v2.office_spec import (
    ConnectionStmt,
    Endpoint,
    OfficeSpec,
    RoleRef,
    SinkSpec,
    SourceSpec,
)
from dissyslab.office_v2.parser import parse_office_dir


# ── Source and sink construction (delegates to v1 registries) ──────────


def _import_class(import_stmt: str, class_name: str):
    """Resolve ``import_stmt`` and return the named class.

    Used to instantiate registry-backed source/sink classes whose
    import path is stored as a string in
    ``dissyslab.office.utils.SOURCE_REGISTRY`` / ``SINK_REGISTRY``.
    """
    import importlib

    module_path = (
        import_stmt.split("import")[0].replace("from ", "").strip()
    )
    module = importlib.import_module(module_path)
    return getattr(module, class_name)


def _build_source(spec: SourceSpec) -> Source:
    """Materialise a ``Source`` from a ``SourceSpec`` using SOURCE_REGISTRY.

    Behaviour mirrors v1 ``office_compiler.build_and_run`` so the
    gallery keeps working unchanged. Long-run we want sources to live
    in the role library too, but that is a Step-8 concern.
    """
    # Imported lazily so the compiler does not pull in feedparser etc.
    # at import time.
    from dissyslab.office.utils import (
        SOURCE_REGISTRY,
        expand_shortcut,
    )

    name = spec.name
    args = dict(spec.args)
    reg = SOURCE_REGISTRY.get(name)
    if reg is None:
        raise CompileError(
            f"unknown source {name!r}. Known sources: "
            f"{sorted(SOURCE_REGISTRY.keys())}"
        )

    if reg["type"] == "rss":
        import dissyslab.components.sources.rss_normalizer as rss_normalizer
        factory = getattr(rss_normalizer, name)
        obj = factory(**args)
    elif reg["type"] == "mcp_shortcut":
        kwargs = expand_shortcut(name, args)
        cls = _import_class(reg["import"], reg["class"])
        obj = cls(**kwargs)
    else:
        cls = _import_class(reg["import"], reg["class"])
        obj = cls(**args) if args else cls()

    return Source(fn=obj.run, name=name)


def _build_sink(spec: SinkSpec) -> Sink:
    """Materialise a ``Sink`` from a ``SinkSpec`` using SINK_REGISTRY."""
    from dissyslab.office.utils import SINK_REGISTRY

    name = spec.name
    args = dict(spec.args)
    reg = SINK_REGISTRY.get(name)
    if reg is None:
        raise CompileError(
            f"unknown sink {name!r}. Known sinks: "
            f"{sorted(SINK_REGISTRY.keys())}"
        )

    cls = _import_class(reg["import"], reg["class"])
    obj = cls(**args) if args else cls()
    return Sink(fn=getattr(obj, reg["call"]), name=name)


# ── Connection translation ─────────────────────────────────────────────


def _translate_connections(
    spec: OfficeSpec, table: _BlockTable
) -> List[Tuple[str, str, str, str]]:
    """Walk ``spec.connections`` and emit runtime 4-tuples.

    Each ``ConnectionStmt`` with N destinations expands into N
    4-tuples. The runtime accepts a flat list and handles fanout
    later.
    """
    out: List[Tuple[str, str, str, str]] = []
    for stmt in spec.connections:
        from_name, from_port = (
            stmt.source.name,
            _runtime_outport(stmt.source.name, stmt.source.port, table),
        )
        for dest in stmt.destinations:
            to_name, to_port = (
                dest.name,
                _runtime_inport(dest.name, dest.port, table),
            )
            out.append((from_name, from_port, to_name, to_port))
    return out


# ── The compiler itself ────────────────────────────────────────────────


def compile_office(
    office_dir: Union[str, Path],
    library: Optional[Library] = None,
) -> Tuple[Network, List[CompileWarning]]:
    """Compile one office directory into a runtime ``Network``.

    Parameters
    ----------
    office_dir
        Filesystem path to the office. Must contain ``office.md``
        (or, for v1 backward compatibility, ``network.md``).
    library
        Optional explicit role library. When ``None``, the compiler
        loads roles from ``<office_dir>/roles_lib/`` and falls back
        to ``<office_dir>/roles/``. The override applies to this
        office only; sub-offices load their own libraries when the
        compiler recurses.

    Returns
    -------
    (Network, list[CompileWarning])
        A fully validated runtime Network plus a list of non-fatal
        observations. Hard errors are raised as ``CompileError``.

    Notes for first-year readers
    ----------------------------
    The returned Network is a plain ``dissyslab.network.Network`` —
    the same kind of object you would build by hand. Calling
    ``net.run_network()`` starts it; ``net.compile()`` lets you
    inspect the flattened agent graph without running.
    """
    office_dir = Path(office_dir).resolve()
    spec = parse_office_dir(office_dir)
    if library is None:
        library = _load_office_library(office_dir)

    warnings: List[CompileWarning] = []
    network = _emit_network(spec, library, office_dir, warnings)
    return network, warnings


def _emit_network(
    spec: OfficeSpec,
    library: Library,
    office_dir: Path,
    warnings: List[CompileWarning],
) -> Network:
    """Walk an OfficeSpec once and produce a runtime Network."""
    blocks: Dict[str, Union[Agent, Network]] = {}
    table = _BlockTable()

    # Sources first — connection statements may reference them by
    # name, and the v1 grammar lets sources fan out.
    for src_spec in spec.sources:
        if src_spec.name in blocks:
            raise CompileError(
                f"duplicate block name {src_spec.name!r} in {spec.name!r}"
            )
        blocks[src_spec.name] = _build_source(src_spec)
        table.sources[src_spec.name] = None

    # Sinks.
    for snk_spec in spec.sinks:
        if snk_spec.name in blocks:
            raise CompileError(
                f"duplicate block name {snk_spec.name!r} in {spec.name!r}"
            )
        blocks[snk_spec.name] = _build_sink(snk_spec)
        table.sinks[snk_spec.name] = None

    # Agents and sub-offices, uniform RoleRefs.
    for ref in spec.agents:
        if ref.agent_name in blocks:
            raise CompileError(
                f"duplicate block name {ref.agent_name!r} in {spec.name!r}"
            )
        block, kind, ports = _resolve_role_ref(
            ref, library, office_dir, warnings
        )
        blocks[ref.agent_name] = block
        if kind == "role":
            table.role_agents[ref.agent_name] = ports
        else:  # subnetwork
            table.subnetworks[ref.agent_name] = ports

    connections = _translate_connections(spec, table)

    # Hand off to the runtime — its check() validates wiring.
    return Network(
        name=spec.name,
        blocks=blocks,
        connections=connections,
        inports=list(spec.inputs),
        outports=list(spec.outputs),
    )


def _resolve_role_ref(
    ref: RoleRef,
    library: Library,
    office_dir: Path,
    warnings: List[CompileWarning],
) -> Tuple[Union[Agent, Network], str, Tuple[str, ...]]:
    """Resolve a single ``RoleRef`` to a runtime block.

    Returns ``(block, kind, out_ports)`` where ``kind`` is
    ``"role"`` or ``"subnetwork"`` and ``out_ports`` is the tuple
    of (semantic) outport names the connection translator will use
    when this block appears as a connection source.
    """
    entry = library.get(ref.role_name)

    if isinstance(entry, AgentRoleEntry):
        block = entry()
        return block, "role", entry.out_ports

    if isinstance(entry, OfficeRoleEntry):
        child_dir = _resolve_subpath(office_dir, entry.path)
        child_net, child_warnings = compile_office(child_dir)
        warnings.extend(child_warnings)
        return child_net, "subnetwork", tuple(child_net.outports)

    if entry is not None:
        raise CompileError(
            f"role {ref.role_name!r} in library is neither an "
            f"AgentRoleEntry nor an OfficeRoleEntry "
            f"(got {type(entry).__name__})"
        )

    # Not in library. Inline-path sugar?
    if ref.path is not None:
        warnings.append(
            CompileWarning(
                message=(
                    f"agent {ref.agent_name!r} uses inline 'office at "
                    f"<path>' sugar — consider adding an explicit "
                    f"OfficeRoleEntry({ref.role_name!r}, "
                    f"path={ref.path!r}) to roles_lib/"
                ),
                location=str(office_dir),
            )
        )
        child_dir = _resolve_subpath(office_dir, ref.path)
        child_net, child_warnings = compile_office(child_dir)
        warnings.extend(child_warnings)
        return child_net, "subnetwork", tuple(child_net.outports)

    raise CompileError(
        f"agent {ref.agent_name!r} uses role {ref.role_name!r}, but "
        f"no such role is in the library and no inline path was "
        f"provided. Library keys: {sorted(library.keys())}"
    )


__all__ = [
    "CompileError",
    "CompileWarning",
    "compile_office",
]
