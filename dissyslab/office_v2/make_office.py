"""
make_office — write an OfficeSpec back to disk as an office folder.

The inverse of ``parse_office_dir``. Where the parser reads markdown
into an ``OfficeSpec``, ``make_office`` writes an ``OfficeSpec`` out
as markdown. The resulting folder is shape-identical to a hand-written
gallery office: ``compile_office``, ``dsl run``, and ``dsl build``
treat it the same.

Why this exists
===============

Pat (the small-business owner who'd benefit from AI automation but
doesn't program for a living) makes an office one of two ways:

1. **By hand.** She opens her editor and writes ``office.md`` and
   the role files in ``roles/``, exactly as the gallery offices are
   written today.
2. **Programmatically.** A higher-level tool (a wizard, a CLI helper,
   a future LLM-driven assembler) constructs an ``OfficeSpec`` and
   the relevant library dicts in Python, then calls
   ``make_office(...)`` to materialise the folder on disk.

Path 2 lets a tool author offices without templating markdown by
hand. Both paths produce the same artifact. Once the folder exists,
nothing downstream cares which path produced it.

V1 scope
========

This first version writes ``office.md``. It does **not** write files
into ``target_dir/roles/``: Pat (or the calling tool) is responsible
for ensuring every role used in ``spec.agents`` resolves at compile
time, either via the framework's built-in role library at
``dissyslab/roles/`` or via files Pat places in ``target_dir/roles/``
herself. The ``roles_lib`` parameter is taken in the signature for
completeness and forward compatibility — a future version will use
it to write any role not in the built-in library out to
``target_dir/roles/`` so the resulting folder is self-contained.

The function is the smallest useful inverse of the parser. It does
not call an LLM, run a wizard, or attempt any verification. Pat
reviews the produced ``office.md`` herself.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, List, Mapping, Optional

from dissyslab.office_v2.library import RoleEntry
from dissyslab.office_v2.office_spec import (
    ConnectionStmt,
    Endpoint,
    OfficeSpec,
    RoleRef,
    SinkSpec,
    SourceSpec,
)
from dissyslab.office_v2.office_spec_constants import EXTERNAL


def make_office(
    target_dir: Path,
    spec: OfficeSpec,
    roles_lib: Mapping[str, RoleEntry],
    fn_lib: Optional[Mapping[str, Callable]] = None,
    office_lib: Optional[Mapping[str, Any]] = None,
) -> Path:
    """Write an ``OfficeSpec`` to disk as an office folder.

    Parameters
    ----------
    target_dir
        Where to create the office folder. Must not already exist.
        Parent directories are created as needed.
    spec
        The office description to materialise.
    roles_lib
        Mapping of role-name → ``RoleEntry``. Reserved in v1 for
        forward compatibility; a future version will use it to write
        non-built-in roles out to ``target_dir/roles/`` so the folder
        is self-contained.
    fn_lib
        Reserved.
    office_lib
        Reserved.

    Returns
    -------
    Path
        ``target_dir``, the freshly-created folder.

    Raises
    ------
    FileExistsError
        If ``target_dir`` already exists. Pick a fresh path —
        ``make_office`` does not overwrite.
    """
    target_dir = Path(target_dir)
    if target_dir.exists():
        raise FileExistsError(
            f"make_office: target_dir already exists: {target_dir}. "
            f"Pick a fresh path; make_office does not overwrite."
        )

    target_dir.mkdir(parents=True)

    md_text = _render_office_md(spec)
    (target_dir / "office.md").write_text(md_text, encoding="utf-8")

    return target_dir


# ── Rendering an OfficeSpec back to office.md text ────────────────────


def _render_office_md(spec: OfficeSpec) -> str:
    """Render an ``OfficeSpec`` to office.md text.

    Designed to round-trip with ``parse_office_dir`` — the produced
    text, parsed, yields a structurally equal spec.
    """
    lines: List[str] = []
    lines.append(f"# Office: {spec.name}")
    lines.append("")

    if spec.inputs:
        lines.append(f"Inputs: {', '.join(spec.inputs)}")
    if spec.outputs:
        lines.append(f"Outputs: {', '.join(spec.outputs)}")
    if spec.inputs or spec.outputs:
        lines.append("")

    if spec.sources:
        lines.append(
            "Sources: "
            + ", ".join(_format_source_or_sink(s) for s in spec.sources)
        )
    if spec.sinks:
        lines.append(
            "Sinks: "
            + ", ".join(_format_source_or_sink(s) for s in spec.sinks)
        )
    if spec.sources or spec.sinks:
        lines.append("")

    if spec.agents:
        lines.append("Agents:")
        for ref in spec.agents:
            lines.append(_format_agent_line(ref))
        lines.append("")

    if spec.connections:
        lines.append("Connections:")
        for stmt in spec.connections:
            lines.append(_format_connection(stmt))
        lines.append("")

    return "\n".join(lines)


def _format_source_or_sink(s) -> str:
    """Render a ``SourceSpec`` or ``SinkSpec`` as ``name`` or ``name(args)``."""
    if not s.args:
        return s.name
    args_str = ", ".join(f"{k}={v!r}" for k, v in s.args)
    return f"{s.name}({args_str})"


def _format_agent_line(ref: RoleRef) -> str:
    """Render a ``RoleRef`` as ``X is a Y.`` or ``X is an office at P.``."""
    if ref.path is not None:
        return f"{ref.agent_name} is an office at {ref.path}."
    article = "an" if ref.role_name[:1].lower() in "aeiou" else "a"
    return f"{ref.agent_name} is {article} {ref.role_name}."


def _format_connection(stmt: ConnectionStmt) -> str:
    """Render a ``ConnectionStmt`` as a single-line ``X's port is/are …``.

    Three cases for the sender side:

    - ``stmt.source.name == EXTERNAL`` — boundary input. The port
      held the input name (parser normalisation). Render back as
      ``<input_name>'s destination`` to match the v1 source-style
      grammar that produces this normalisation.
    - Source agent (port == "destination" by convention) — render as
      ``<source_name>'s destination``.
    - Anything else (regular agent, sub-office) — ``<name>'s <port>``.

    The first two collapse into the same generic
    ``<name>'s <port>`` form because boundary inputs use the
    convention of port == ``"destination"`` *implicitly* — the parser
    stored the *input* name in the port slot, but to round-trip we
    treat that as the original ``<input>'s destination`` line.
    """
    src = stmt.source
    if src.name == EXTERNAL:
        # Boundary input: src.port holds the input name; original line
        # was '<input>'s destination is …'.
        src_label = f"{src.port}'s destination"
    else:
        src_label = f"{src.name}'s {src.port}"

    dest_strs = [_format_destination(d) for d in stmt.destinations]
    if len(dest_strs) == 1:
        recipients = dest_strs[0]
        copula = "is"
    elif len(dest_strs) == 2:
        recipients = f"{dest_strs[0]} and {dest_strs[1]}"
        copula = "are"
    else:
        recipients = ", ".join(dest_strs[:-1]) + f" and {dest_strs[-1]}"
        copula = "are"

    return f"{src_label} {copula} {recipients}."


def _format_destination(ep: Endpoint) -> str:
    """Render a destination ``Endpoint`` to its destination phrase.

    Three cases:

    - ``EXTERNAL`` — boundary output. Render as just the port name;
      the office's ``Outputs:`` section establishes the mapping.
    - Implicit single-inport ``"in_"`` — render as bare name.
    - Explicit port — render as ``name's port``.
    """
    if ep.name == EXTERNAL:
        return ep.port
    if ep.port == "in_":
        return ep.name
    return f"{ep.name}'s {ep.port}"


__all__ = ["make_office"]
