"""
Layer 6 — codegen: emit a readable ``run.py`` for an office tree.

``compile_office`` (Layer 5) builds a runtime ``Network`` by walking
parser output and a role library. Codegen does the same walk, but
instead of building Python objects it writes Python *source*. The
result is a single self-explanatory file students can open and
trace, line-for-line, back to their ``office.md``.

What gets emitted
=================

For an office tree rooted at ``<office_dir>`` we write
``<office_dir>/build/run.py``. The file:

* imports ``Network``, ``Source``, ``Sink``, and the source/sink
  classes the office actually uses (one ``import`` per registry
  entry, deduplicated);
* defines a small ``_load_lib(office_dir)`` helper, then loads each
  office's role library exactly once at module level into a
  ``_ROLES_<OFFICE>`` mapping;
* emits one ``build_<office>() -> Network`` function per office in
  the tree, in topological order (children before parents);
* if the top office is closed (no Inputs/Outputs), ends with
  ``if __name__ == "__main__": build_<top>().run_network()``.

The generated code mirrors what ``compile_office`` produces. It is
the same ``Network`` either way; codegen exists so students can read
the wiring as a Python module they own, not as a black-box object.

Connection comments
===================

Each connection 4-tuple gets a side-of-line comment that bridges
the runtime indexed port name back to the office.md vocabulary:

    ("Alex", "out_0", "Morgan", "in_"),    # Alex's briefing → Morgan

so a student can grep ``run.py`` for the same words they wrote.

Path conventions
================

Library paths in the generated code are resolved relative to
``__file__`` (the run.py itself) so the artifact is portable as long
as the office tree stays intact around it. Sub-office paths follow
the v2 idiom — relative to the parent office's directory.
"""
from __future__ import annotations

import os
import re
import textwrap
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from dissyslab.fn_lib import FN_LIB, partition_kwargs
from dissyslab.office.library import PARAMETERIZED_LIBRARY
from dissyslab.office._internals import (
    CompileError,
    _BlockTable,
    _load_office_library,
    _resolve_subpath,
    _runtime_inport,
    _runtime_outport,
)
from dissyslab.office.library import (
    AgentRoleEntry,
    Library,
    OfficeRoleEntry,
)
from dissyslab.office.office_spec import (
    ConnectionStmt,
    Endpoint,
    OfficeSpec,
    RoleRef,
    SinkSpec,
    SourceSpec,
)
from dissyslab.office.office_spec_constants import EXTERNAL
from dissyslab.office.parser import parse_office_dir


# ── Tree of offices to emit ───────────────────────────────────────────


@dataclass
class _OfficeNode:
    """One office in the dependency tree, with codegen metadata.

    The codegen walk visits each office once even if it is referenced
    multiple times by parents (the same sub-office can be embedded
    twice). Children appear in source order; the topological emit
    order ensures every child function is defined before any caller
    references it.
    """

    name: str          # Python-safe identifier derived from spec.name
    raw_name: str      # the original from office.md
    spec: OfficeSpec
    library: Library
    office_dir: Path
    table: _BlockTable
    # children: list of (agent_name_in_parent, child_node)
    children: List[Tuple[str, "_OfficeNode"]] = field(default_factory=list)
    # Agents resolved from fn_lib (instead of roles_lib): maps
    # agent_name → (role_name, init_kwargs, fn_kwargs). The emitter
    # uses these to generate Transform construction lines, with
    # ``init_kwargs`` going to ``initial_state(...)`` and
    # ``fn_kwargs`` going into ``params=``.
    fn_lib_agents: Dict[
        str, Tuple[str, Dict[str, Any], Dict[str, Any]]
    ] = field(default_factory=dict)
    # Agents resolved from PARAMETERIZED_LIBRARY: maps
    # agent_name → (role_name, kwargs). The emitter generates a
    # ``PARAMETERIZED_LIBRARY[role](**kwargs)()`` call at runtime.
    parameterized_agents: Dict[
        str, Tuple[str, Dict[str, Any]]
    ] = field(default_factory=dict)


def _sanitize(s: str) -> str:
    """Coerce an office name into a Python-safe identifier suffix."""
    s = re.sub(r"[^A-Za-z0-9_]", "_", s)
    if not s or s[0].isdigit():
        s = "_" + s
    return s


def _build_tree(
    office_dir: Path,
    library: Optional[Library] = None,
    cache: Optional[Dict[Path, "_OfficeNode"]] = None,
) -> _OfficeNode:
    """Recursively gather codegen metadata for an office and its children.

    Mirrors ``compile_office``'s walk but skips block instantiation —
    we never call ``entry.factory()`` or open any source. The
    resulting tree carries enough information (port shapes, sub-office
    structure) for emission.
    """
    if cache is None:
        cache = {}
    office_dir = office_dir.resolve()
    if office_dir in cache:
        return cache[office_dir]

    spec = parse_office_dir(office_dir)
    if library is None:
        library = _load_office_library(office_dir)

    node = _OfficeNode(
        name=_sanitize(spec.name),
        raw_name=spec.name,
        spec=spec,
        library=library,
        office_dir=office_dir,
        table=_BlockTable(),
    )
    cache[office_dir] = node

    for src in spec.sources:
        node.table.sources[src.name] = None
    for snk in spec.sinks:
        node.table.sinks[snk.name] = None

    for ref in spec.agents:
        entry = library.get(ref.role_name)
        if isinstance(entry, AgentRoleEntry):
            node.table.role_agents[ref.agent_name] = entry.out_ports
        elif isinstance(entry, OfficeRoleEntry):
            child_dir = _resolve_subpath(office_dir, entry.path)
            child = _build_tree(child_dir, library=None, cache=cache)
            node.children.append((ref.agent_name, child))
            node.table.subnetworks[ref.agent_name] = tuple(
                child.spec.outputs
            )
        elif entry is None and ref.path is not None:
            child_dir = _resolve_subpath(office_dir, ref.path)
            child = _build_tree(child_dir, library=None, cache=cache)
            node.children.append((ref.agent_name, child))
            node.table.subnetworks[ref.agent_name] = tuple(
                child.spec.outputs
            )
        elif entry is not None:
            raise CompileError(
                f"role {ref.role_name!r} in library is neither an "
                f"AgentRoleEntry nor an OfficeRoleEntry "
                f"(got {type(entry).__name__})"
            )
        elif ref.role_name in PARAMETERIZED_LIBRARY:
            # Parameterized library role — port shape depends on the
            # kwargs Pat wrote in office.md. We invoke the constructor
            # now (purely to discover out_ports for downstream wiring
            # validation) but record the kwargs for the emitter, which
            # re-invokes at runtime inside build/run.py.
            constructor = PARAMETERIZED_LIBRARY[ref.role_name]
            user_kwargs = dict(ref.args)
            try:
                entry = constructor(**user_kwargs)
            except TypeError as exc:
                raise CompileError(
                    f"agent {ref.agent_name!r}: bad arguments to "
                    f"parameterized role {ref.role_name!r}: {exc}"
                ) from exc
            except ValueError as exc:
                raise CompileError(
                    f"agent {ref.agent_name!r}: {exc}"
                ) from exc
            node.table.role_agents[ref.agent_name] = entry.out_ports
            node.parameterized_agents[ref.agent_name] = (
                ref.role_name, user_kwargs
            )
        elif ref.role_name in FN_LIB:
            # fn_lib role — single semantic outport "out", runtime "out_".
            fn_entry = FN_LIB[ref.role_name]
            init_kwargs, fn_kwargs, unknown = partition_kwargs(
                fn_entry, dict(ref.args)
            )
            if unknown:
                raise CompileError(
                    f"agent {ref.agent_name!r}: unknown argument(s) "
                    f"{sorted(unknown)} for fn_lib role "
                    f"{ref.role_name!r}. Neither initial_state nor fn "
                    f"accepts these names."
                )
            node.table.role_agents[ref.agent_name] = ("out",)
            node.fn_lib_agents[ref.agent_name] = (
                ref.role_name, init_kwargs, fn_kwargs
            )
        else:
            raise CompileError(
                f"agent {ref.agent_name!r} uses role {ref.role_name!r}, "
                f"but no such role is in the library, no inline path "
                f"was provided, and no fn_lib or parameterized-library "
                f"entry of that name exists.\n"
                f"  roles_lib keys:              {sorted(library.keys())}\n"
                f"  fn_lib keys:                 {sorted(FN_LIB.keys())}\n"
                f"  PARAMETERIZED_LIBRARY keys:  {sorted(PARAMETERIZED_LIBRARY.keys())}"
            )

    return node


def _topo_order(root: _OfficeNode) -> List[_OfficeNode]:
    """Children-before-parents traversal, deduplicated by office_dir."""
    out: List[_OfficeNode] = []
    seen: set = set()

    def visit(node: _OfficeNode) -> None:
        if node.office_dir in seen:
            return
        seen.add(node.office_dir)
        for _, child in node.children:
            visit(child)
        out.append(node)

    visit(root)
    return out


# ── Emission helpers ──────────────────────────────────────────────────


def _kwargs_repr(args: Dict[str, Any]) -> str:
    """Render ``{a: 1, b: 'x'}`` as ``"a=1, b='x'"`` for code emission."""
    return ", ".join(f"{k}={v!r}" for k, v in args.items())


def _conn_comment(src: Endpoint, dest: Endpoint) -> str:
    """Side-of-line comment bridging runtime ports back to office.md vocabulary."""
    if src.name == EXTERNAL:
        src_label = f"external '{src.port}'"
    else:
        src_label = f"{src.name}'s {src.port}"
    if dest.name == EXTERNAL:
        dest_label = f"external '{dest.port}'"
    elif dest.port == "in_":
        dest_label = dest.name
    else:
        dest_label = f"{dest.name}'s {dest.port}"
    return f"{src_label} → {dest_label}"


def _emit_source(
    src: SourceSpec, indent: str
) -> Tuple[List[str], Optional[str]]:
    """Return (lines, import_stmt). ``import_stmt`` may be None for RSS.

    Looks up the source name in the unified COMPONENT_REGISTRY via
    ``lookup_component`` and validates that its ``kind`` is
    ``"source"``. A kind mismatch produces a Pat-readable warning in
    the generated artifact (the runtime will surface the same error
    via the compiler; codegen prefers to emit a runnable file that
    is loud about the misuse rather than refusing to generate).
    """
    from dissyslab.office.utils import expand_shortcut, lookup_component

    entry = lookup_component(src.name)
    if entry is None:
        return (
            [
                f"{indent}# WARNING: unknown source {src.name!r}; "
                f"will fail at runtime"
            ],
            None,
        )

    if entry["kind"] != "source":
        return (
            [
                f"{indent}# WARNING: {src.name!r} is a {entry['kind']}, "
                f"not a source; will fail at runtime"
            ],
            None,
        )

    args = dict(src.args)

    if entry.get("type") == "rss":
        ctor = f"rss_normalizer.{src.name}({_kwargs_repr(args)})"
        import_stmt = (
            "import dissyslab.components.sources.rss_normalizer "
            "as rss_normalizer"
        )
    elif entry.get("type") == "rss_generic":
        ctor = f'{entry["class"]}({_kwargs_repr(args)})'
        import_stmt = entry["import"]
    elif entry.get("type") == "web_scraper_factory":
        ctor = f"web_scraper.{src.name}({_kwargs_repr(args)})"
        import_stmt = (
            "import dissyslab.components.sources.web_scraper "
            "as web_scraper"
        )
    elif entry.get("type") == "mcp_shortcut":
        kwargs = expand_shortcut(src.name, args)
        ctor = f'{entry["class"]}({_kwargs_repr(kwargs)})'
        import_stmt = entry["import"]
    else:
        ctor = f'{entry["class"]}({_kwargs_repr(args)})'
        import_stmt = entry["import"]

    lines = [
        f"{indent}_{src.name} = {ctor}",
        f"{indent}{src.name} = Source("
        f"fn=_{src.name}.run, name={src.name!r})",
    ]
    return lines, import_stmt


def _emit_sink(
    snk: SinkSpec, indent: str
) -> Tuple[List[str], Optional[str]]:
    """Return (lines, import_stmt)."""
    from dissyslab.office.utils import lookup_component

    entry = lookup_component(snk.name)
    if entry is None:
        return (
            [
                f"{indent}# WARNING: unknown sink {snk.name!r}; "
                f"will fail at runtime"
            ],
            None,
        )

    if entry["kind"] != "sink":
        return (
            [
                f"{indent}# WARNING: {snk.name!r} is a {entry['kind']}, "
                f"not a sink; will fail at runtime"
            ],
            None,
        )

    args = dict(snk.args)
    ctor = f'{entry["class"]}({_kwargs_repr(args)})'
    lines = [
        f"{indent}_{snk.name} = {ctor}",
        f"{indent}{snk.name} = Sink("
        f"fn=_{snk.name}.{entry['call']}, name={snk.name!r})",
    ]
    return lines, entry["import"]


def _emit_builder(node: _OfficeNode) -> str:
    """Emit the source text of one ``build_<office>()`` function."""
    lines: List[str] = []
    lines.append(f"def build_{node.name}() -> Network:")
    lines.append(
        f'    """Build runtime Network for office {node.raw_name!r}."""'
    )

    # Sources first.
    for src in node.spec.sources:
        src_lines, _ = _emit_source(src, indent="    ")
        lines.extend(src_lines)

    # Sinks.
    for snk in node.spec.sinks:
        snk_lines, _ = _emit_sink(snk, indent="    ")
        lines.extend(snk_lines)

    if node.spec.sources or node.spec.sinks:
        lines.append("")

    # Network construction.
    lines.append("    return Network(")
    lines.append(f"        name={node.raw_name!r},")
    lines.append("        blocks={")

    roles_var = f"_ROLES_{node.name.upper()}"
    for src in node.spec.sources:
        lines.append(f'            "{src.name}": {src.name},')
    for snk in node.spec.sinks:
        lines.append(f'            "{snk.name}": {snk.name},')

    for ref in node.spec.agents:
        # An AI override (``Qwen's AI is ollama.``) is only meaningful
        # for LLM roles built via ``nl_role`` — i.e. the plain-role
        # branch below. Catching it here gives a clear error rather
        # than a TypeError at runtime when someone writes
        # ``Sync's AI is anthropic.`` for a synchronizer.
        if ref.ai_backend is not None and (
            ref.agent_name in node.table.subnetworks
            or ref.agent_name in node.fn_lib_agents
            or ref.agent_name in node.parameterized_agents
        ):
            raise CompileError(
                f"agent {ref.agent_name!r} is not an LLM role, so "
                f"\"'s AI is\" override has no effect. Drop the "
                f"\"{ref.agent_name}'s AI is {ref.ai_backend}.\" line "
                f"from office.md, or move it to an agent backed by a "
                f"role.md file."
            )

        if ref.agent_name in node.table.subnetworks:
            child = next(
                c for n, c in node.children if n == ref.agent_name
            )
            lines.append(
                f'            "{ref.agent_name}": build_{child.name}(),'
            )
        elif ref.agent_name in node.fn_lib_agents:
            role_name, init_kwargs, fn_kwargs = node.fn_lib_agents[
                ref.agent_name
            ]
            fn_kwargs_repr = "{" + ", ".join(
                f"{k!r}: {v!r}" for k, v in fn_kwargs.items()
            ) + "}"
            init_call_kwargs = _kwargs_repr(init_kwargs)
            entry_ref = f"FN_LIB[{role_name!r}]"
            lines.append(f'            "{ref.agent_name}": Transform(')
            lines.append(f"                fn={entry_ref}.fn,")
            lines.append(f"                params={fn_kwargs_repr},")
            lines.append(
                f"                state={entry_ref}.initial_state("
                f"{init_call_kwargs}),"
            )
            lines.append(f"                name={ref.agent_name!r},")
            lines.append("            ),")
        elif ref.agent_name in node.parameterized_agents:
            role_name, user_kwargs = node.parameterized_agents[
                ref.agent_name
            ]
            kwargs_repr = _kwargs_repr(user_kwargs)
            # The runtime re-invokes the parameterized-library
            # constructor with the same kwargs to obtain a fresh
            # AgentRoleEntry, then calls it to get the Agent. Pat
            # wrote the kwargs once in office.md; the framework
            # uses them at compile time (for port validation) and
            # at runtime (to build the agent).
            lines.append(
                f'            "{ref.agent_name}": '
                f'PARAMETERIZED_LIBRARY[{role_name!r}]('
                f'{kwargs_repr})(),'
            )
        else:
            # Plain LLM role *or* Python AgentRoleEntry role.
            #
            # Forward any office.md kwargs to the role's factory
            # (``Alex is a bird_classifier(min_confidence=0.7).``),
            # together with the optional AI backend override
            # (``Qwen's AI is ollama.``). For LLM roles built via
            # ``nl_role`` the factory accepts ``AI=...``; for
            # Python roles the factory accepts whatever kwargs the
            # role's ``__init__`` declares. Unknown kwargs raise a
            # TypeError at runtime, which is the same behaviour
            # parameterized-library roles already have.
            factory_kwargs = dict(ref.args)
            if ref.ai_backend:
                factory_kwargs["AI"] = ref.ai_backend
            kwargs_repr = _kwargs_repr(factory_kwargs)
            lines.append(
                f'            "{ref.agent_name}": '
                f'{roles_var}[{ref.role_name!r}]({kwargs_repr}),'
            )

    lines.append("        },")
    lines.append("        connections=[")

    for stmt in node.spec.connections:
        from_port = _runtime_outport(
            stmt.source.name, stmt.source.port, node.table
        )
        for dest in stmt.destinations:
            to_port = _runtime_inport(
                dest.name, dest.port, node.table
            )
            comment = _conn_comment(stmt.source, dest)
            lines.append(
                f"            ({stmt.source.name!r}, {from_port!r}, "
                f"{dest.name!r}, {to_port!r}),    # {comment}"
            )

    lines.append("        ],")
    if node.spec.inputs:
        lines.append(f"        inports={list(node.spec.inputs)!r},")
    if node.spec.outputs:
        lines.append(f"        outports={list(node.spec.outputs)!r},")
    lines.append("    )")
    return "\n".join(lines)


def _emit_imports(nodes: List[_OfficeNode]) -> str:
    """Collate every import the generated code needs, deduplicated."""
    base = [
        "from pathlib import Path",
        "",
        "import dissyslab",
        "from dissyslab.network import Network",
        "from dissyslab.blocks.source import Source",
        "from dissyslab.blocks.sink import Sink",
        "from dissyslab.blocks.transform import Transform",
        "from dissyslab.fn_lib import FN_LIB",
        "from dissyslab.office import (",
        "    PARAMETERIZED_LIBRARY,",
        "    load_roles_dir,",
        ")",
        "",
    ]

    seen: set = set()
    extra: List[str] = []
    for node in nodes:
        for src in node.spec.sources:
            _, imp = _emit_source(src, indent="")
            if imp and imp not in seen:
                extra.append(imp)
                seen.add(imp)
        for snk in node.spec.sinks:
            _, imp = _emit_sink(snk, indent="")
            if imp and imp not in seen:
                extra.append(imp)
                seen.add(imp)

    return "\n".join(base + extra)


def _emit_library_loads(
    nodes: List[_OfficeNode], top_dir: Path
) -> str:
    """Module-level ``_ROLES_<OFFICE>`` declarations, one per office."""
    run_py_dir = top_dir / "build"
    lines = [
        "",
        "_HERE = Path(__file__).resolve().parent",
        "_BUILTIN_ROLES = Path(dissyslab.__file__).resolve().parent / 'roles'",
        "",
        "",
        "def _load_lib(office_dir: Path):",
        '    """Load <office_dir>/roles plus the framework\'s built-in roles.',
        '',
        '    Same convention as office.compiler — office-local entries',
        '    win over built-ins of the same name.',
        '    """',
        "    builtin = load_roles_dir(_BUILTIN_ROLES)",
        "    local = load_roles_dir(office_dir / 'roles')",
        "    return {**builtin, **local}",
        "",
        "",
    ]
    for node in nodes:
        var = f"_ROLES_{node.name.upper()}"
        rel = os.path.relpath(node.office_dir, run_py_dir)
        lines.append(f"{var} = _load_lib(_HERE / {rel!r})")
    return "\n".join(lines)


def _emit_main(root: _OfficeNode) -> str:
    """If the root office is closed, emit the ``__main__`` runner block.

    The runner picks between ``run_network()`` (threads, the default —
    correct for I/O-bound work) and ``process_network()`` (OS
    processes, true CPU parallelism) based on the ``DSL_PROCESS_MODE``
    environment variable. Pat does not see this choice; ``dsl run``
    exposes ``--processes`` as a power-user flag that sets the env
    var before invoking the artifact.
    """
    if root.spec.is_open():
        return ""
    return (
        "\n\n"
        "if __name__ == \"__main__\":\n"
        "    import os\n"
        "    # Run from the office directory so relative paths in\n"
        "    # office.md (audio_clip(path=\"./samples/...\"),\n"
        "    # jsonl_recorder(path=\"out.jsonl\"), etc.) resolve next\n"
        "    # to the office regardless of where dsl run was invoked.\n"
        "    os.chdir(str(_HERE.parent))\n"
        f"    _office = build_{root.name}()\n"
        "    if os.environ.get(\"DSL_PROCESS_MODE\") == \"process\":\n"
        "        _office.process_network()\n"
        "    else:\n"
        "        _office.run_network()\n"
    )


def _emit_header(root: _OfficeNode) -> str:
    """Module docstring at the top of run.py."""
    return (
        f'"""run.py — generated by office codegen for '
        f'office {root.raw_name!r}.\n\n'
        f"Do not edit by hand. Re-run `dsl build` to regenerate.\n\n"
        f"This file is plain Python: read it to see exactly which\n"
        f"agents, sources, and sinks the office wires together, and\n"
        f"how. Calling `build_{root.name}().run_network()` starts\n"
        f"the system; that is also what the `__main__` block at the\n"
        f"bottom does for closed offices.\n"
        f'"""\n'
    )


# ── Public API ────────────────────────────────────────────────────────


def render_run_py(
    office_dir: Any, library: Optional[Library] = None
) -> str:
    """Build the source text of ``run.py`` for an office tree.

    Returns the file contents as a string. ``emit_run_py`` writes
    that string to disk; tests usually call ``render_run_py`` so
    they can assert on the text without touching the filesystem.
    """
    office_dir = Path(office_dir).resolve()
    root = _build_tree(office_dir, library)
    nodes = _topo_order(root)

    parts = [
        _emit_header(root),
        _emit_imports(nodes),
        _emit_library_loads(nodes, office_dir),
        "",
        "",
        "\n\n\n".join(_emit_builder(n) for n in nodes),
        _emit_main(root),
    ]
    return "\n".join(parts)


def emit_run_py(
    office_dir: Any, library: Optional[Library] = None
) -> Path:
    """Render ``run.py`` and write it to ``<office_dir>/build/run.py``.

    Returns the absolute path of the written file. Creates
    ``<office_dir>/build/`` and a sibling ``__init__.py`` if needed.
    """
    office_dir = Path(office_dir).resolve()
    text = render_run_py(office_dir, library)
    out_dir = office_dir / "build"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "run.py"
    out_path.write_text(text, encoding="utf-8")
    init = out_dir / "__init__.py"
    if not init.exists():
        init.write_text("")
    return out_path


__all__ = [
    "emit_run_py",
    "render_run_py",
]
