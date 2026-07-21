# dissyslab/office/from_officespeak.py
"""
The Phase 3 generator: an OfficeSpeakSpec -> a runnable office folder.

Three mechanical steps, in order:

1. **Translate** an `OfficeSpeakSpec` (OfficeSpeak's own vocabulary -- see
   `officespeak_spec.py`) into a `dissyslab.office.office_spec.OfficeSpec`
   (DisSysLab's own vocabulary). The only judgment call in this step is
   which DisSysLab role a registered coordinator maps to, and that's a
   fixed lookup table, not generation.
2. **Write role files** for every office-specific (`transform`) agent, from
   its already-*approved* body (`phase3_approval.md`'s exit criteria) --
   wrap a Python `fn` in `Role`, or write a prompt straight to `roles/*.md`.
   No code or prompt is written here that wasn't already approved.
3. **Call `make_office()`** (already exists, already tested, already what
   every hand-written gallery office round-trips through) to materialise
   `office.md`, then write the role files alongside it.

What this deliberately does *not* do: match a Phase 2 source/sink
description against DisSysLab's registered library (task #34 -- the
`OfficeSpeakSpec` already carries the resolved registered name), or decide
message shapes (Phase 1's Pass A/Pass B already fixed those; this only
wires to them).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Tuple

from dissyslab.blocks.role import Role
from dissyslab.office.library import AgentRoleEntry
from dissyslab.office.make_office import make_office
from dissyslab.office.office_spec import (
    ConnectionStmt,
    Endpoint,
    OfficeSpec,
    RoleRef,
    SinkSpec,
    SourceSpec,
)
from dissyslab.office.officespeak_spec import AgentSpec, OfficeSpeakSpec

_IMPLICIT_INPORT = "in_"  # every office-specific agent's one inbox


class GeneratorError(ValueError):
    """Raised when an OfficeSpeakSpec can't be translated -- always with
    enough detail to fix the spec, never a silent guess."""


# ── Step 1a: coordinator kind -> DisSysLab role_name + kwargs ──────────
#
# Each function takes the AgentSpec (a "coordinator"-kind agent, in
# OfficeSpeak's own vocabulary) and returns (dissyslab_role_name, kwargs)
# for the RoleRef the compiler will resolve via PARAMETERIZED_LIBRARY.
# Every one of these also validates that the agent's *outbox* name matches
# what the underlying role always uses -- "out" (a single declared outport;
# the compiler maps that to the runtime "out_" regardless of the string
# chosen, but only if every connection naming this agent's outbox uses that
# same string).


def _require_single_out(agent: AgentSpec) -> None:
    if tuple(agent.out_ports) != ("out",):
        raise GeneratorError(
            f"agent {agent.name!r} is a {agent.registered_as!r} coordinator; "
            f"its single outbox must be declared as \"out\" (got "
            f"{list(agent.out_ports)!r}) to match the registered role's "
            f"fixed out_ports."
        )


def _translate_merge_synch(agent: AgentSpec) -> Tuple[str, Dict[str, Any]]:
    _require_single_out(agent)
    if not agent.in_ports:
        raise GeneratorError(f"merge_synch agent {agent.name!r} has no declared inports")
    return "synchronizer", {"inports": list(agent.in_ports)}


def _translate_select(agent: AgentSpec) -> Tuple[str, Dict[str, Any]]:
    _require_single_out(agent)
    if "command" not in agent.in_ports:
        raise GeneratorError(
            f"select agent {agent.name!r} has no inport named \"command\" "
            f"(declared: {list(agent.in_ports)!r}). select needs one inport "
            f"reserved as the command port that tells it what to read next "
            f"-- see start_gallery/trading_room.md. This can't be guessed; "
            f"either Phase 1 didn't produce one, or it used a different "
            f"name. Resolve by hand before generating this office."
        )
    data_ports = [p for p in agent.in_ports if p != "command"]
    if not data_ports:
        raise GeneratorError(f"select agent {agent.name!r} has a command port but no data inports")
    return "select", {"inports": data_ports, "command": "command"}


def _translate_gate(agent: AgentSpec) -> Tuple[str, Dict[str, Any]]:
    _require_single_out(agent)
    if set(agent.in_ports) != {"data", "control"}:
        raise GeneratorError(
            f"gate agent {agent.name!r} must have exactly the inports "
            f"\"data\" and \"control\" (got {list(agent.in_ports)!r}) -- "
            f"these are gate's fixed names per start_instructions_v3.md, "
            f"not a convention to guess at."
        )
    return "gate", {"data": "data", "control": "control"}


def _translate_record(agent: AgentSpec) -> Tuple[str, Dict[str, Any]]:
    _require_single_out(agent)
    initial = agent.registered_args.get("initial")
    if initial is not None and not isinstance(initial, dict):
        raise GeneratorError(f"record agent {agent.name!r} registered_args['initial'] must be a dict or absent, got {initial!r}")
    # Default, per Mani's decision: a record with no stated initial values
    # starts holding nothing (record_role's own default) rather than
    # blocking generation on Phase 2 having specified one.
    return "record", {"initial": initial}


_COORDINATOR_TRANSLATORS = {
    "merge_synch": _translate_merge_synch,
    "select": _translate_select,
    "gate": _translate_gate,
    "record": _translate_record,
}


# ── Step 1b: build the DisSysLab OfficeSpec ────────────────────────────


def _build_office_spec(spec: OfficeSpeakSpec) -> Tuple[OfficeSpec, Dict[str, str]]:
    """Translate an OfficeSpeakSpec into a DisSysLab OfficeSpec.

    Returns the spec plus a name map (OfficeSpeak's agent name -> the name
    used inside the generated office.md), since a source/sink agent's
    office.md-visible name is its *registered* name, not whatever Phase 1
    called it -- DisSysLab's ``Sources:``/``Sinks:`` lines have no separate
    alias mechanism.
    """
    name_map: Dict[str, str] = {}
    sources = []
    sinks = []
    agent_refs = []

    for agent in spec.agents:
        if agent.kind == "source":
            sources.append(SourceSpec(name=agent.registered_as, args=tuple(agent.registered_args.items())))
            name_map[agent.name] = agent.registered_as
        elif agent.kind == "sink":
            sinks.append(SinkSpec(name=agent.registered_as, args=tuple(agent.registered_args.items())))
            name_map[agent.name] = agent.registered_as
        elif agent.kind == "coordinator":
            translator = _COORDINATOR_TRANSLATORS.get(agent.registered_as)
            if translator is None:
                raise GeneratorError(
                    f"agent {agent.name!r} has coordinator kind "
                    f"{agent.registered_as!r}; must be one of "
                    f"{sorted(_COORDINATOR_TRANSLATORS)}"
                )
            role_name, kwargs = translator(agent)
            agent_refs.append(RoleRef(agent_name=agent.name, role_name=role_name, args=tuple(kwargs.items())))
            name_map[agent.name] = agent.name
        else:  # "transform"
            # role_name is this agent's own name, lowercased -- a fresh
            # role file is written for every transform, one-to-one, so
            # there's no collision risk in picking a systematic name.
            role_name = agent.name.lower()
            agent_refs.append(RoleRef(agent_name=agent.name, role_name=role_name))
            name_map[agent.name] = agent.name

    source_names = {a.name for a in spec.agents if a.kind == "source"}
    sink_names = {a.name for a in spec.agents if a.kind == "sink"}

    connections = []
    for c in spec.connections:
        sender_name = name_map.get(c.sender)
        receiver_name = name_map.get(c.receiver)
        if sender_name is None:
            raise GeneratorError(f"connection references unknown agent {c.sender!r}")
        if receiver_name is None:
            raise GeneratorError(f"connection references unknown agent {c.receiver!r}")
        if c.sender in source_names and c.sender_port not in ("destination", "out"):
            raise GeneratorError(
                f"connection from source {c.sender!r} must use sender_port "
                f'"destination" or "out" (checked directly against the '
                f"compiler: dissyslab/office/_internals.py's "
                f"_runtime_outport maps *any* string a source's outport is "
                f"called to the literal runtime \"out_\", so both are "
                f"equally valid -- \"destination\" for existing hand-written "
                f"offices, \"out\" for consistency with every other agent "
                f"kind and with Track A's own bare-outbox-naming rule), got "
                f"{c.sender_port!r}"
            )
        if c.receiver in sink_names and c.receiver_port != "in_":
            raise GeneratorError(
                f"connection to sink {c.receiver!r} must use receiver_port "
                f'"in_" (every sink has exactly one inbox), got {c.receiver_port!r}'
            )
        src = Endpoint(name=sender_name, port=c.sender_port)
        dst = Endpoint(name=receiver_name, port=c.receiver_port)
        connections.append(ConnectionStmt(source=src, destinations=(dst,)))

    # Merge connections that share the same (sender, sender_port) into one
    # ConnectionStmt with multiple destinations -- office.md's fan-out form
    # ("X's out is Y and Z.") -- matching make_office's own rendering,
    # which writes one line per distinct sender/outport.
    merged: Dict[Tuple[str, str], list] = {}
    order: list = []
    for stmt in connections:
        key = (stmt.source.name, stmt.source.port)
        if key not in merged:
            merged[key] = []
            order.append(key)
        merged[key].extend(stmt.destinations)
    connections = [
        ConnectionStmt(source=Endpoint(name=key[0], port=key[1]), destinations=tuple(dests))
        for key, dests in ((k, merged[k]) for k in order)
    ]

    office_spec = OfficeSpec(
        name=spec.name,
        sources=tuple(sources),
        sinks=tuple(sinks),
        agents=tuple(agent_refs),
        connections=tuple(connections),
    )
    return office_spec, name_map


# ── Step 2: write role files for office-specific agents ────────────────


def _write_role_files(target_dir: Path, spec: OfficeSpeakSpec) -> None:
    roles_dir = target_dir / "roles"
    roles_dir.mkdir(parents=True, exist_ok=True)

    for agent in spec.agents:
        if agent.kind != "transform":
            continue
        role_name = agent.name.lower()
        body = agent.body

        if body.kind == "python":
            _write_python_role(roles_dir, role_name, agent, body.fn)
        else:
            _write_prompt_role(roles_dir, role_name, body.prompt)


def _write_python_role(roles_dir: Path, role_name: str, agent: AgentSpec, fn_factory) -> None:
    """Write roles/<role_name>.py wrapping an approved factory in Role.

    ``fn_factory`` is a zero-arg callable that, called once per agent
    instantiation, returns the real ``handler(msg) -> results`` -- the
    factory shape every hand-written stateful role in this codebase already
    uses, so a fresh closure (a running count, a pending value) is private
    per agent. This writes a *reference* to the approved factory via
    ``inspect.getsource`` so the generated file is self-contained and
    reviewable; if the source can't be recovered (e.g. a factory built
    dynamically at runtime rather than defined at module level), that's an
    error -- the caller must supply a source-recoverable factory, matching
    phase3_approval.md's expectation that the approved body is something a
    person already read, not an opaque object.
    """
    import inspect
    import textwrap

    try:
        src = inspect.getsource(fn_factory)
    except (OSError, TypeError) as exc:
        raise GeneratorError(
            f"agent {agent.name!r}: approved fn's source could not be "
            f"recovered ({exc}); the Phase 3 generator needs fn defined in "
            f"an importable module, not built dynamically at runtime."
        ) from exc
    src = textwrap.dedent(src)

    statuses = list(agent.out_ports) or ["out"]
    if len(statuses) == 1:
        statuses = ["out"]  # match Role's own single-status convention

    file_text = (
        f"# dissyslab/gallery/.../roles/{role_name}.py\n"
        f'"""Generated by from_officespeak.py from an approved Phase 2 body.\n'
        f'Agent: {agent.name}\n"""\n\n'
        "from __future__ import annotations\n\n"
        "from typing import Any\n\n"
        "from dissyslab.blocks.role import Role\n"
        "from dissyslab.office.library import AgentRoleEntry\n\n"
        f"{src}\n\n"
        f"role = AgentRoleEntry(\n"
        f"    name={role_name!r},\n"
        f"    in_ports=(\"in_\",),\n"
        f"    out_ports={tuple(statuses)!r},\n"
        f"    factory=lambda: Role(fn={fn_factory.__name__}(), statuses={list(statuses)!r}),\n"
        f")\n"
    )
    (roles_dir / f"{role_name}.py").write_text(file_text, encoding="utf-8")


def _write_prompt_role(roles_dir: Path, role_name: str, prompt: str) -> None:
    (roles_dir / f"{role_name}.md").write_text(prompt, encoding="utf-8")


# ── Step 3: tie it together ─────────────────────────────────────────────


def build_office_from_officespeak(target_dir: Path, spec: OfficeSpeakSpec) -> Path:
    """Materialise an approved OfficeSpeakSpec as a runnable office folder.

    Raises ``GeneratorError`` (never a silent guess) if a coordinator's
    ports don't match what its registered role requires, if a connection
    references an unknown agent, or if a transform's approved Python body
    isn't source-recoverable. ``dsl build``/``compile_office`` still do
    their own, separate validation afterward -- this only guarantees the
    translation step was faithful.
    """
    office_spec, _name_map = _build_office_spec(spec)
    target_dir = Path(target_dir)
    make_office(target_dir, office_spec, roles_lib={})
    _write_role_files(target_dir, spec)
    return target_dir


__all__ = ["GeneratorError", "build_office_from_officespeak"]
