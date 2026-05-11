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
   call on disk; their library is loaded from their own ``roles/``
   plus the framework's built-in ``dissyslab/roles/``.
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
argument, so the child loads its own ``roles/`` (with the framework's
built-in ``dissyslab/roles/`` as fallback). That keeps offices
self-contained and lets the same office work both as a top-level
program and as a sub-office.

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

import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

from dissyslab.core import Agent
from dissyslab.network import Network
from dissyslab.blocks.source import Source
from dissyslab.blocks.sink import Sink
from dissyslab.blocks.transform import Transform
from dissyslab.fn_lib import FN_LIB, partition_kwargs

from dissyslab.office_v2._internals import (
    CompileError,
    CompileWarning,
    _BlockTable,
    _load_office_library,
    _resolve_subpath,
    _runtime_inport,
    _runtime_outport,
    _suggest,
)
from dissyslab.office_v2.office_spec_constants import EXTERNAL
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


_UNEXPECTED_KW_RE = re.compile(
    r"unexpected keyword argument ['\"]([A-Za-z_][A-Za-z0-9_]*)['\"]"
)


def _accepted_kwargs(callable_obj) -> list:
    """Return the list of keyword names ``callable_obj`` accepts.

    Used to produce "Did you mean?" suggestions on a bad kwarg. Falls
    back to an empty list if the signature cannot be introspected
    (some C-implemented callables refuse).
    """
    import inspect
    try:
        sig = inspect.signature(callable_obj)
    except (TypeError, ValueError):
        return []
    names = []
    for p in sig.parameters.values():
        if p.kind in (
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
            inspect.Parameter.KEYWORD_ONLY,
        ):
            if p.name != "self":
                names.append(p.name)
    return names


def _construct_or_pat_error(
    callable_obj, args: dict, *, kind: str, name: str
):
    """Call ``callable_obj(**args)`` and translate TypeError to CompileError.

    ``kind`` is ``"source"`` or ``"sink"``; ``name`` is the registry
    entry name. On a bad kwarg, the message names the offending key,
    offers a "Did you mean?" against the accepted parameters, and lists
    the keyword names the constructor actually takes.
    """
    try:
        return callable_obj(**args) if args else callable_obj()
    except TypeError as exc:
        msg = str(exc)
        m = _UNEXPECTED_KW_RE.search(msg)
        if m is None:
            # Not a kwarg-name problem — surface the original message
            # but framed for Pat.
            raise CompileError(
                f"Failed to build {kind} {name!r}: {exc}"
            ) from exc
        bad = m.group(1)
        accepted = _accepted_kwargs(callable_obj)
        hint = _suggest(bad, accepted)
        parts = [
            f"Argument {bad!r} is not valid for {kind} {name!r}."
        ]
        if hint:
            parts.append(hint)
        if accepted:
            parts.append(
                f"Valid arguments: {', '.join(accepted)}."
            )
        raise CompileError(" ".join(parts)) from exc


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
        known = sorted(SOURCE_REGISTRY.keys())
        hint = _suggest(name, known)
        parts = [f"Unknown source {name!r}."]
        if hint:
            parts.append(hint)
        parts.append(f"Known sources: {', '.join(known)}.")
        raise CompileError(" ".join(parts))

    if reg["type"] == "rss":
        import dissyslab.components.sources.rss_normalizer as rss_normalizer
        factory = getattr(rss_normalizer, name)
        obj = _construct_or_pat_error(
            factory, args, kind="source", name=name
        )
    elif reg["type"] == "mcp_shortcut":
        kwargs = expand_shortcut(name, args)
        cls = _import_class(reg["import"], reg["class"])
        obj = _construct_or_pat_error(
            cls, kwargs, kind="source", name=name
        )
    else:
        cls = _import_class(reg["import"], reg["class"])
        obj = _construct_or_pat_error(
            cls, args, kind="source", name=name
        )

    return Source(fn=obj.run, name=name)


def _build_sink(spec: SinkSpec) -> Sink:
    """Materialise a ``Sink`` from a ``SinkSpec`` using SINK_REGISTRY."""
    from dissyslab.office.utils import SINK_REGISTRY

    name = spec.name
    args = dict(spec.args)
    reg = SINK_REGISTRY.get(name)
    if reg is None:
        known = sorted(SINK_REGISTRY.keys())
        hint = _suggest(name, known)
        parts = [f"Unknown sink {name!r}."]
        if hint:
            parts.append(hint)
        parts.append(f"Known sinks: {', '.join(known)}.")
        raise CompileError(" ".join(parts))

    cls = _import_class(reg["import"], reg["class"])
    obj = _construct_or_pat_error(cls, args, kind="sink", name=name)
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
        loads roles from ``<office_dir>/roles/`` and falls back to
        the framework's built-in ``dissyslab/roles/``. The override
        applies to this office only; sub-offices load their own
        libraries when the compiler recurses.

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

    _validate_connection_endpoints(spec, blocks)
    connections = _translate_connections(spec, table)

    # Hand off to the runtime — its check() validates wiring.
    return Network(
        name=spec.name,
        blocks=blocks,
        connections=connections,
        inports=list(spec.inputs),
        outports=list(spec.outputs),
    )


def _validate_connection_endpoints(
    spec: OfficeSpec, blocks: Dict[str, Union[Agent, Network]]
) -> None:
    """Pre-validate that every connection refers to a known block.

    Without this pass, a typo like ``bbc_world's destination is sinky.``
    reaches the runtime's ``Network.check()`` and surfaces as a
    cryptic wiring complaint. Catching it here lets us emit a
    Pat-shaped message that names the offending identifier and offers
    a "Did you mean?" suggestion against the names actually declared
    in this office.

    External endpoints (Inputs/Outputs of an open office, represented
    by the parser as ``Endpoint("external", <port>)``) are validated
    against the office's declared ``inputs`` / ``outputs`` rather
    than against ``blocks``.
    """
    known = set(blocks.keys())
    inputs = set(spec.inputs)
    outputs = set(spec.outputs)
    for stmt in spec.connections:
        src = stmt.source
        if src.name == EXTERNAL:
            if src.port not in inputs:
                hint = _suggest(src.port, inputs)
                parts = [
                    f"Connection sender refers to external input "
                    f"{src.port!r}, but no such input is declared "
                    f"in the Inputs: section."
                ]
                if hint:
                    parts.append(hint)
                if inputs:
                    parts.append(
                        f"Declared inputs: {', '.join(sorted(inputs))}."
                    )
                raise CompileError(" ".join(parts))
        else:
            if src.name not in known:
                hint = _suggest(src.name, known)
                parts = [
                    f"Connection refers to sender {src.name!r}, but "
                    f"no source, sink, or agent of that name is "
                    f"declared in this office."
                ]
                if hint:
                    parts.append(hint)
                if known:
                    parts.append(
                        f"Known names: {', '.join(sorted(known))}."
                    )
                raise CompileError(" ".join(parts))
        for dest in stmt.destinations:
            if dest.name == EXTERNAL:
                if dest.port not in outputs:
                    hint = _suggest(dest.port, outputs)
                    parts = [
                        f"Connection recipient refers to external "
                        f"output {dest.port!r}, but no such output "
                        f"is declared in the Outputs: section."
                    ]
                    if hint:
                        parts.append(hint)
                    if outputs:
                        parts.append(
                            f"Declared outputs: "
                            f"{', '.join(sorted(outputs))}."
                        )
                    raise CompileError(" ".join(parts))
            else:
                if dest.name not in known:
                    hint = _suggest(dest.name, known)
                    parts = [
                        f"Connection refers to recipient "
                        f"{dest.name!r}, but no source, sink, or "
                        f"agent of that name is declared in this "
                        f"office."
                    ]
                    if hint:
                        parts.append(hint)
                    if known:
                        parts.append(
                            f"Known names: "
                            f"{', '.join(sorted(known))}."
                        )
                    raise CompileError(" ".join(parts))


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

    # Not in roles_lib. Try fn_lib (framework-shipped Python
    # transformers). Office-local roles win if both define the same
    # name, because the roles_lib lookup happens first.
    fn_entry = FN_LIB.get(ref.role_name)
    if fn_entry is not None:
        user_kwargs = dict(ref.args)
        init_kwargs, fn_kwargs, unknown = partition_kwargs(
            fn_entry, user_kwargs
        )
        if unknown:
            raise CompileError(
                f"agent {ref.agent_name!r}: unknown argument(s) "
                f"{sorted(unknown)} for fn_lib role "
                f"{ref.role_name!r}. Neither initial_state nor fn "
                f"accepts these names."
            )
        try:
            initial_state = fn_entry.initial_state(**init_kwargs)
        except TypeError as exc:
            raise CompileError(
                f"agent {ref.agent_name!r}: bad arguments to fn_lib "
                f"role {ref.role_name!r}: {exc}"
            ) from exc
        block = Transform(
            fn=fn_entry.fn,
            params=fn_kwargs,
            state=initial_state,
            name=ref.agent_name,
        )
        # Single semantic outport called "out". The runtime translates
        # it to "out_" via the single-output convention; Pat writes
        # ``Sasha's out is <dest>.`` in office.md.
        return block, "role", ("out",)

    # Not in library. Inline-path sugar?
    if ref.path is not None:
        warnings.append(
            CompileWarning(
                message=(
                    f"agent {ref.agent_name!r} uses inline 'office at "
                    f"<path>' sugar — consider adding an explicit "
                    f"OfficeRoleEntry({ref.role_name!r}, "
                    f"path={ref.path!r}) to roles/"
                ),
                location=str(office_dir),
            )
        )
        child_dir = _resolve_subpath(office_dir, ref.path)
        child_net, child_warnings = compile_office(child_dir)
        warnings.extend(child_warnings)
        return child_net, "subnetwork", tuple(child_net.outports)

    all_roles = sorted(set(library.keys()) | set(FN_LIB.keys()))
    hint = _suggest(ref.role_name, all_roles)
    parts = [
        f"Agent {ref.agent_name!r} uses role {ref.role_name!r}, "
        f"but no such role is defined.",
    ]
    if hint:
        parts.append(hint)
    parts.append(
        f"To fix: add a prompt file at roles/{ref.role_name}.md "
        f"(or an explicit OfficeRoleEntry), or correct the spelling."
    )
    if all_roles:
        parts.append(f"Known roles: {', '.join(all_roles)}.")
    raise CompileError(" ".join(parts))


__all__ = [
    "CompileError",
    "CompileWarning",
    "compile_office",
]
