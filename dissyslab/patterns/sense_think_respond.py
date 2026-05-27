"""
Sense → think → respond pattern, made operational as a Python builder.

This module is the executable form of the pattern documented in
``docs/PATTERN_sense_think_respond.md``.

Call :func:`build_office` with the pattern's four picks
— sources, parallel thinkers, writer, sinks — plus a target
directory; the function writes a working ``office.md`` (and a
per-office ``roles/synchronizer.py``) ready for ``dsl run``.

The wiring is fixed by the pattern::

    sources → gate (deduplicator) → parallel thinkers
        → synchronizer → writer → sinks

For other network shapes, use a different builder (or hand-write
office.md directly).

Naming
======

The function name uses the abbreviation ``str_pipeline`` for
"sense → think → respond pipeline" to reserve the more general name
``build_office`` for a future generic builder that supports
arbitrary topologies. Other patterns will get their own builders
in this subpackage (e.g. ``build_feedback_loop_office``).

What the builder does NOT do
============================

* It does not write role prompts. Each role named in ``thinkers``
  or ``writer`` must already exist either in the office's local
  ``target/roles/`` directory or in the framework's built-in role
  library at ``dissyslab/roles/``. (Pat-shaped offices typically
  pick from the built-in library; domain-specific offices add
  custom role files locally.)
* It does not copy or modify role files; the office.md just names
  them and the compiler resolves at run time.
* It does not register sources or sinks. Each ``sources`` and
  ``sinks`` entry must already be a registered name in
  ``SOURCE_REGISTRY`` or ``SINK_REGISTRY`` respectively.

What the builder DOES write
===========================

* ``target/office.md`` — the office description, with the standard
  s→t→r wiring, annotated with the four ``# SLOT N:`` comments so
  Pat can edit it.
* ``target/roles/synchronizer.py`` — a per-office synchronizer
  whose named inports match the thinker role names. Each office
  needs its own because the inports depend on which thinkers Pat
  chose.

Pat's hand-edits to ``office.md`` after generation are preserved —
the generated office is hers to modify. The builder is a one-time
scaffold, not a runtime input.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Sequence, Tuple, Union

# ── Type aliases ──────────────────────────────────────────────────────

#: A source pick: either a bare registry name or ``(name, kwargs)``.
SourceSpec = Union[str, Tuple[str, dict]]

#: A sink pick: either a bare registry name or ``(name, kwargs)``.
SinkSpec = Union[str, Tuple[str, dict]]

#: An agent pick: ``(agent_name, role_name)``.
AgentSpec = Tuple[str, str]


# ── Public API ────────────────────────────────────────────────────────


def build_office(
    *,
    name: str,
    target: Union[str, Path],
    sources: Sequence[SourceSpec],
    thinkers: Sequence[AgentSpec],
    writer: AgentSpec,
    publish_sinks: Sequence[SinkSpec],
    discard_sinks: Sequence[SinkSpec] = (),
    gate: Tuple[str, str, dict] = ("Sasha", "deduplicator", {"by": "url"}),
    sync_agent: str = "Sync",
) -> Path:
    """Generate a sense → think → respond office at ``target/``.

    Parameters
    ----------
    name
        The office name (goes in the ``# Office: <name>`` header).
    target
        Directory to write into. Created if missing.
    sources
        List of source picks. Each entry is either a registry name
        like ``"bbc_world"`` or a tuple ``(name, kwargs)`` like
        ``("bbc_world", {"max_articles": 5})``.
    thinkers
        List of ``(agent_name, role_name)`` tuples — the parallel
        thinkers in SLOT 2. Each role must exist either in
        ``target/roles/`` or in the framework's built-in library.
    writer
        ``(agent_name, role_name)`` for the writer agent (SLOT 3).
    publish_sinks
        List of sink picks (same shape as sources) for the writer's
        kept output. Required.
    discard_sinks
        Optional list of sink picks for the writer's "not worth
        publishing" output. When empty, the writer has a single
        outport ``out``. When non-empty, the writer is wired with
        two outports ``publish`` and ``discard``; the caller's
        writer role file must declare both (e.g., ``Send to
        publish.`` / ``Send to discard.``).
    gate
        Three-tuple ``(agent_name, role_name, kwargs)`` for the
        deduplicator gate at the front of the pipeline. Defaults
        to deduplication by ``url``.
    sync_agent
        Name of the synchronizer agent. Defaults to ``"Sync"``.

    Returns
    -------
    Path
        The resolved target directory.

    Example
    -------
    Regenerate ``situation_room`` (without the now-removed evaluator)::

        build_office(
            name="situation_room",
            target="./gen_situation_room",
            sources=[
                ("bbc_world",  {"max_articles": 1}),
                ("npr_news",   {"max_articles": 1}),
                ("al_jazeera", {"max_articles": 1}),
            ],
            thinkers=[
                ("Eve",   "entity_extractor"),
                ("Sam",   "severity_classifier"),
                ("Tom",   "topic_tagger"),
                ("Greta", "geolocator"),
            ],
            writer=("Riley", "writer"),
            publish_sinks=[
                "intelligence_display",
                ("jsonl_recorder_briefing", {"path": "briefings.jsonl"}),
            ],
            discard_sinks=[
                ("jsonl_recorder_discard", {"path": "rejected.jsonl"}),
            ],
        )
    """
    target = Path(target).resolve()
    target.mkdir(parents=True, exist_ok=True)
    (target / "roles").mkdir(exist_ok=True)

    office_md = _render_office_md(
        name=name,
        sources=sources,
        thinkers=thinkers,
        writer=writer,
        publish_sinks=publish_sinks,
        discard_sinks=discard_sinks,
        gate=gate,
        sync_agent=sync_agent,
    )
    (target / "office.md").write_text(office_md, encoding="utf-8")

    sync_py = _render_synchronizer_py(thinkers=thinkers)
    (target / "roles" / "synchronizer.py").write_text(
        sync_py, encoding="utf-8"
    )

    return target


# ── Helpers ───────────────────────────────────────────────────────────


def _render_decl(spec: Union[str, Tuple[str, dict]]) -> str:
    """Render a source or sink spec to its office.md form.

    ``"hacker_news"`` → ``"hacker_news"``.
    ``("hacker_news", {"max_articles": 5})`` →
    ``"hacker_news(max_articles=5)"``.
    """
    if isinstance(spec, str):
        return spec
    name, kwargs = spec
    if not kwargs:
        return name
    args_str = ", ".join(f"{k}={v!r}" for k, v in kwargs.items())
    return f"{name}({args_str})"


def _name_of(spec: Union[str, Tuple[str, dict]]) -> str:
    """Bare registry name from a source/sink spec."""
    return spec if isinstance(spec, str) else spec[0]


def _sync_inport_for(role_name: str) -> str:
    """The inport name on the synchronizer for a thinker with this role.

    We mechanically use the role name itself — readable in office.md
    (``Eve's out is Sync's entity_extractor.``) and easy to match
    against in the generated synchronizer.py.
    """
    return role_name


def _article_for(role_name: str) -> str:
    """Choose ``"a"`` vs ``"an"`` for natural office.md prose."""
    return "an" if role_name[:1].lower() in "aeiou" else "a"


def _render_office_md(
    *,
    name: str,
    sources: Sequence[SourceSpec],
    thinkers: Sequence[AgentSpec],
    writer: AgentSpec,
    publish_sinks: Sequence[SinkSpec],
    discard_sinks: Sequence[SinkSpec],
    gate: Tuple[str, str, dict],
    sync_agent: str,
) -> str:
    """Render the office.md text for the given picks."""
    gate_name, gate_role, gate_kwargs = gate
    writer_name, writer_role = writer

    lines: list[str] = []
    lines.append(f"# Office: {name}")
    lines.append("")
    lines.append(
        "# An instance of the sense → think → respond pattern; see"
    )
    lines.append(
        "# docs/PATTERN_sense_think_respond.md."
    )
    lines.append("")

    source_strs = [_render_decl(s) for s in sources]
    lines.append(f"Sources: {', '.join(source_strs)}")
    all_sinks = list(publish_sinks) + list(discard_sinks)
    sink_strs = [_render_decl(s) for s in all_sinks]
    lines.append(f"Sinks: {', '.join(sink_strs)}")
    lines.append("")

    lines.append("Agents:")
    if gate_kwargs:
        gate_args = ", ".join(
            f"{k}={v!r}" for k, v in gate_kwargs.items()
        )
        lines.append(
            f"{gate_name} is {_article_for(gate_role)} "
            f"{gate_role}({gate_args})."
        )
    else:
        lines.append(
            f"{gate_name} is {_article_for(gate_role)} {gate_role}."
        )
    for agent_name, role_name in thinkers:
        lines.append(
            f"{agent_name} is {_article_for(role_name)} {role_name}."
        )
    lines.append(f"{sync_agent} is a synchronizer.")
    lines.append(
        f"{writer_name} is {_article_for(writer_role)} {writer_role}."
    )
    lines.append("")

    # ── Connections ──
    lines.append("Connections:")
    # sources → gate
    for spec in sources:
        lines.append(f"{_name_of(spec)}'s destination is {gate_name}.")
    lines.append("")

    # gate → thinkers (fan-out)
    thinker_names = [t[0] for t in thinkers]
    lines.append(f"{gate_name}'s out is {', '.join(thinker_names)}.")
    lines.append("")

    # thinkers → synchronizer (named ports)
    for agent_name, role_name in thinkers:
        port = _sync_inport_for(role_name)
        lines.append(f"{agent_name}'s out is {sync_agent}'s {port}.")
    lines.append("")

    # synchronizer → writer
    lines.append(f"{sync_agent}'s out is {writer_name}.")

    # writer → sinks
    publish_names = [_name_of(s) for s in publish_sinks]
    discard_names = [_name_of(s) for s in discard_sinks]
    if discard_sinks:
        # Two-outport writer.
        lines.append(
            f"{writer_name}'s publish is {', '.join(publish_names)}."
        )
        lines.append(
            f"{writer_name}'s discard is {', '.join(discard_names)}."
        )
    else:
        # Single-outport writer.
        lines.append(
            f"{writer_name}'s out is {', '.join(publish_names)}."
        )

    return "\n".join(lines) + "\n"


def _render_synchronizer_py(*, thinkers: Sequence[AgentSpec]) -> str:
    """Render a per-office synchronizer.py.

    The synchronizer's inports match the thinker role names so the
    generated office.md's ``Eve's out is Sync's entity_extractor.``
    style wiring lines up with the runtime.
    """
    inports = [_sync_inport_for(role) for _, role in thinkers]
    inports_repr = ", ".join(repr(p) for p in inports)
    n = len(inports)
    inport_list = ", ".join(inports)

    return (
        '"""Per-office synchronizer.\n\n'
        "Auto-generated by\n"
        "`dissyslab.patterns.sense_think_respond.build_office`.\n\n"
        f"Waits for one message on each of {n} named inports — "
        f"{inport_list} — dict-merges the messages,\n"
        'and emits the merged article on `out`.\n'
        '"""\n'
        "from dissyslab.core import Agent\n"
        "from dissyslab.office import AgentRoleEntry\n"
        "\n"
        "\n"
        "class _Synchronizer(Agent):\n"
        "    def __init__(self, name=None):\n"
        "        super().__init__(\n"
        "            name=name,\n"
        f"            inports=[{inports_repr}],\n"
        '            outports=["out_"],\n'
        "        )\n"
        "\n"
        "    def run(self) -> None:\n"
        "        while True:\n"
        "            merged: dict = {}\n"
        "            for inport in self.inports:\n"
        "                msg = self.recv(inport)\n"
        "                if isinstance(msg, dict):\n"
        "                    merged.update(msg)\n"
        '            self.send(merged, "out_")\n'
        "\n"
        "\n"
        "role = AgentRoleEntry(\n"
        '    name="synchronizer",\n'
        f"    in_ports=({inports_repr},),\n"
        '    out_ports=("out",),\n'
        "    factory=_Synchronizer,\n"
        "    description=(\n"
        f'        "Wait for one message on each of {n} inports — "\n'
        f'        "{inport_list} — dict-merge, emit on out."\n'
        "    ),\n"
        ")\n"
    )


__all__ = ["build_office"]
