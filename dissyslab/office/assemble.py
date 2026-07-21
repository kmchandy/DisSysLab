# dissyslab/office/assemble.py
"""
The last mechanical step: a filled-in draft -> a runnable office.

This is the piece that did not exist before -- everything it calls
(``build_office_from_officespeak``, ``OfficeSpeakSpec`` and friends) was
already built and validated earlier this session. What was missing was
purely clerical: turning Track A's own output plus Al's decisions into the
dataclasses the generator expects, without Al hand-writing any of that
wiring.

The division of labor this closes
==================================

- **Track A** (a plain-English conversation, no Python) ends by emitting a
  *draft* file -- see ``dissyslab/office/draft_template.py`` for the exact
  shape -- with every agent, port, connection, and plain-English description
  already filled in (Track A knows all of this already; Phase 1/2 is
  explicitly scoped to never write code or a prompt itself). Every
  source/sink's ``registered_as`` and every transform's ``body_fn``/
  ``body_prompt``/``approved`` start out blank.
- **Al** (typically working *with* Claude, not alone -- see the
  Al-Claude-conversation transcripts) fills those blanks in: matches each
  source/sink (``phase3_source_sink_matching.md``), drafts each transform's
  actual code or prompt from its Phase 2 description, tests or reads it,
  and flips ``approved=True`` (``phase3_approval.md``). Al ends up editing
  and extending an already-structured file, not writing an office from
  scratch.
- **This module** reads the finished draft, validates every blank is
  filled, builds the real ``OfficeSpeakSpec``, and calls the existing
  generator. Al's action is one command:
  ``python -m dissyslab.office.assemble <draft.py> <target_dir>``.

Why a ``.py`` draft, not YAML/JSON
==================================

A transform's approved body is *real code* (a zero-arg factory function) or
a prompt string -- not data a text format can represent directly. Making the
draft itself a plain Python file lets Track A write the factory function
for real, as an ordinary top-level ``def``, exactly as it already does in
conversation -- Al edits the same file to test and refine it, with no
separate serialization step. The non-code parts (kind, ports, connections,
``registered_as``) are just plain literals (strings, lists, dicts) in that
same file -- filling them in is data entry, not programming.

What is deliberately *not* re-solved here
==========================================

No source/sink matching (that is ``phase3_source_sink_matching.md``'s job,
done by Al before running this). No worker approval (``phase3_approval.md``,
also Al, also before this). No message-shape or coordination-primitive
decisions (Phase 1/2, already fixed). This module's only job is turning
already-finished decisions into the generator's input shape, plus one
mechanical normalization rule (below) that is easy to forget by hand and has
no reason to be re-decided per office.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

from dissyslab.office.officespeak_spec import (
    AgentSpec,
    ConnectionSpec,
    OfficeSpeakSpec,
    WorkerBody,
)
from dissyslab.office.from_officespeak import build_office_from_officespeak


class AssemblyError(ValueError):
    """Raised when a draft isn't finished yet or is malformed -- always
    naming exactly which agent and which field, never a silent guess."""


# ── Loading the draft file ──────────────────────────────────────────────


def _load_draft_module(draft_path: Path):
    """Import a draft file as a Python module, by path.

    The draft is real Python (function definitions plus plain literals),
    so it is loaded the normal way modules are loaded from a path --
    not parsed as data. This means a draft with a genuine Python syntax
    error fails exactly the way editing any other Python file would;
    there is no separate parser to keep in sync with what Track A emits.
    """
    draft_path = Path(draft_path).resolve()
    if not draft_path.is_file():
        raise AssemblyError(f"draft file not found: {draft_path}")
    spec = importlib.util.spec_from_file_location("_officespeak_draft", draft_path)
    if spec is None or spec.loader is None:
        raise AssemblyError(f"could not load {draft_path} as a Python module")
    module = importlib.util.module_from_spec(spec)
    # Registered under a fixed name so a factory function's __module__
    # resolves consistently if anything downstream needs it (mirrors how
    # a normal import works); harmless to overwrite on repeat runs.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _require_attr(module, name: str, draft_path: Path) -> Any:
    if not hasattr(module, name):
        raise AssemblyError(
            f"draft {draft_path} is missing top-level `{name}` -- every "
            f"draft must define OFFICE_NAME, AGENTS, and CONNECTIONS."
        )
    return getattr(module, name)


# ── Validating + building each agent ────────────────────────────────────


def _build_agent_spec(agent: Dict[str, Any]) -> Tuple[AgentSpec, str, str, str]:
    """Validate one draft agent dict and build its AgentSpec.

    Returns ``(agent_spec, name, old_out_port_or_"", old_in_port_or_"")``.
    The third/fourth elements are whatever Track A originally called this
    agent's single outbox/inbox, *only* when this agent needed one of the
    port-naming normalizations below -- so the caller can rewrite matching
    connections to the real runtime name. Empty string means no rename.

    Three normalization rules, applied unconditionally, none of them
    something Al should have to know or remember:

    1. **A transform/sink's single inbox is always ``in_`` at runtime**
       (``officespeak_spec.ConnectionSpec``'s own docstring: "every
       office-specific agent has exactly one inbox, always named in_").
       Track A, faithful to its own taught rule ("name a lone inbox
       `in`"), writes the bare name ``in`` -- a real, previously
       undiscovered mismatch, caught by actually running a cold instance's
       hand-off file through this assembler (see
       cold_tests/transcripts/ -- the room-climate-monitor case).
    2. **A transform with exactly one outbox is always ``out``** (see
       ``from_officespeak.py``'s ``_write_python_role``) -- the rule
       already found and fixed during case 01/02's validation.
    3. **A real registered source's single outbox is ``destination`` or
       ``out``** -- both are accepted, never renamed to each other. Checked
       directly against the compiler (``office/_internals.py``'s
       ``_runtime_outport``): for a source, it maps *any* string to the
       literal runtime ``out_`` -- "destination" was only ever a
       convention hand-written offices happened to use, not something the
       compiler requires, so there is no need to touch existing offices to
       also accept ``out`` (Track A's own bare-outbox-naming rule, "name a
       lone outbox `out`," already produces this for free). Anything
       *other* than these two gets normalized to ``out``, the newer,
       consistent choice -- never to ``destination``.
    """
    name = agent.get("name")
    kind = agent.get("kind")
    if not name or not isinstance(name, str):
        raise AssemblyError(f"an agent dict is missing a valid 'name': {agent!r}")
    if kind not in ("source", "sink", "transform", "coordinator"):
        raise AssemblyError(
            f"agent {name!r}: 'kind' must be one of source/sink/transform/"
            f"coordinator, got {kind!r}"
        )

    in_ports = tuple(agent.get("in_ports", ()))
    out_ports = tuple(agent.get("out_ports", ()))
    old_out = ""
    old_in = ""

    if kind == "source":
        registered_as = agent.get("registered_as")
        if not registered_as:
            raise AssemblyError(
                f"agent {name!r} (source) still has registered_as=None -- "
                f"Al needs to match it against docs/SOURCES_AND_SINKS.md "
                f"(see phase3_source_sink_matching.md), or -- if nothing "
                f"fits -- reclassify it as a transform standing in for one, "
                f"before this can run."
            )
        # Rule 3: "destination" and "out" are both already valid (checked
        # against the compiler); normalize anything else to "out".
        if len(out_ports) == 1 and out_ports[0] not in ("destination", "out"):
            old_out = out_ports[0]
            out_ports = ("out",)
        return (
            AgentSpec(
                name=name, kind=kind, in_ports=in_ports, out_ports=out_ports,
                registered_as=registered_as,
                registered_args=agent.get("registered_args", {}),
            ),
            name, old_out, old_in,
        )

    if kind == "sink":
        registered_as = agent.get("registered_as")
        if not registered_as:
            raise AssemblyError(
                f"agent {name!r} (sink) still has registered_as=None -- "
                f"Al needs to match it against docs/SOURCES_AND_SINKS.md "
                f"(see phase3_source_sink_matching.md) before this can run."
            )
        # Rule 1.
        if len(in_ports) == 1 and in_ports[0] != "in_":
            old_in = in_ports[0]
            in_ports = ("in_",)
        return (
            AgentSpec(
                name=name, kind=kind, in_ports=in_ports, out_ports=out_ports,
                registered_as=registered_as,
                registered_args=agent.get("registered_args", {}),
            ),
            name, old_out, old_in,
        )

    if kind == "coordinator":
        registered_as = agent.get("registered_as")
        if not registered_as:
            raise AssemblyError(
                f"agent {name!r} (coordinator) has no registered_as -- "
                f"Track A already knows this (merge_synch/select/gate/"
                f"record); it should never be blank for a coordinator."
            )
        # Coordinators keep their real, semantic inport/outport names --
        # they are the one kind with more than one inbox, so no "always
        # in_"/"always out" normalization applies to them.
        return (
            AgentSpec(
                name=name, kind=kind, in_ports=in_ports, out_ports=out_ports,
                registered_as=registered_as,
                registered_args=agent.get("registered_args", {}),
            ),
            name, old_out, old_in,
        )

    # kind == "transform"
    if not agent.get("approved"):
        raise AssemblyError(
            f"agent {name!r} (transform) is not approved yet -- Al needs "
            f"to run/read it and flip approved=True (see "
            f"phase3_approval.md) before this can run."
        )
    body_kind = agent.get("body_kind")
    if body_kind == "python":
        fn = agent.get("body_fn")
        if not callable(fn):
            raise AssemblyError(
                f"agent {name!r}: body_kind='python' but body_fn is not "
                f"callable ({fn!r})"
            )
        body = WorkerBody(kind="python", fn=fn)
    elif body_kind == "prompt":
        prompt = agent.get("body_prompt")
        if not (isinstance(prompt, str) and prompt.strip()):
            raise AssemblyError(
                f"agent {name!r}: body_kind='prompt' but body_prompt is "
                f"empty"
            )
        body = WorkerBody(kind="prompt", prompt=prompt)
    else:
        raise AssemblyError(
            f"agent {name!r}: body_kind must be 'python' or 'prompt', got "
            f"{body_kind!r}"
        )

    # Rule 1 (a transform's single inbox) and rule 2 (a transform's single
    # outbox), both applied the same mechanical way.
    if len(in_ports) == 1 and in_ports[0] != "in_":
        old_in = in_ports[0]
        in_ports = ("in_",)
    if len(out_ports) == 1 and out_ports[0] != "out":
        old_out = out_ports[0]
        out_ports = ("out",)

    return (
        AgentSpec(name=name, kind=kind, in_ports=in_ports, out_ports=out_ports, body=body),
        name, old_out, old_in,
    )


def build_spec_from_draft(module) -> OfficeSpeakSpec:
    """Turn a loaded draft module into a real, validated OfficeSpeakSpec."""
    office_name = _require_attr(module, "OFFICE_NAME", Path(module.__file__))
    raw_agents = _require_attr(module, "AGENTS", Path(module.__file__))
    raw_connections = _require_attr(module, "CONNECTIONS", Path(module.__file__))

    agents: List[AgentSpec] = []
    # agent_name -> (original outport name, original inport name) wherever
    # a normalization rule (see _build_agent_spec's docstring) renamed one.
    out_renames: Dict[str, str] = {}
    in_renames: Dict[str, str] = {}
    for raw in raw_agents:
        spec, name, old_out, old_in = _build_agent_spec(raw)
        agents.append(spec)
        if old_out:
            out_renames[name] = old_out
        if old_in:
            in_renames[name] = old_in

    connections: List[ConnectionSpec] = []
    for sender, sender_port, receiver, receiver_port in raw_connections:
        if sender in out_renames and sender_port == out_renames[sender]:
            # The new name is always "destination" for a source, "out"
            # for a transform -- look it up off the agent we just built
            # rather than re-deriving it, to avoid the two rules drifting
            # out of sync with each other.
            sender_port = next(a.out_ports[0] for a in agents if a.name == sender)
        if receiver in in_renames and receiver_port == in_renames[receiver]:
            receiver_port = "in_"
        connections.append(ConnectionSpec(sender, sender_port, receiver, receiver_port))

    return OfficeSpeakSpec(name=office_name, agents=tuple(agents), connections=tuple(connections))


# ── Public entry point ──────────────────────────────────────────────────


def assemble(draft_path: "str | Path", target_dir: "str | Path") -> Path:
    """Read a finished draft and materialize it as a runnable office.

    Raises ``AssemblyError`` naming exactly what's unfinished if any
    agent still has a blank (an unmatched source/sink, an unapproved
    transform) -- never generates from a partially-finished draft.
    """
    module = _load_draft_module(Path(draft_path))
    spec = build_spec_from_draft(module)
    return build_office_from_officespeak(Path(target_dir), spec)


def _main(argv=None) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        prog="python -m dissyslab.office.assemble",
        description=(
            "Turn a finished OfficeSpeak draft (every source/sink matched, "
            "every worker approved) into a runnable office: writes "
            "office.md + roles/ at <target_dir>. Run `dsl build "
            "<target_dir>` and `dsl run <target_dir>` next."
        ),
    )
    parser.add_argument("draft", help="path to the filled-in draft .py file")
    parser.add_argument("target_dir", help="directory to write office.md + roles/ into")
    args = parser.parse_args(argv)

    try:
        target = assemble(args.draft, args.target_dir)
    except AssemblyError as exc:
        print(f"assemble: {exc}", file=sys.stderr)
        return 1
    print(f"  Wrote {target}/office.md and {target}/roles/")
    print(f"  Next: dsl build {target}   (or dsl run {target})")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())


__all__ = ["AssemblyError", "assemble", "build_spec_from_draft"]
