# dissyslab/office/officespeak_spec.py
"""
OfficeSpeakSpec — the input shape `from_officespeak.py`'s generator consumes.

This is *not* what `start_instructions_v3.md` produces directly (that's a
plain-English conversation). It's the small, structured shape a Phase 1/2
conversation's result gets transcribed into before generation -- today, by
hand; later, possibly automatically. Keeping it a plain dataclass (not, say,
raw office.md text) keeps the generator's job mechanical: translate this
into a `dissyslab.office.office_spec.OfficeSpec`, write role files for the
office-specific agents, and hand off to the already-tested `make_office()`.

Four agent kinds, matching `start_instructions_v3.md` exactly ("Every agent
has one of four kinds"):

- **source** / **sink** — resolved by a human against DisSysLab's existing
  registered library (task #34; not this module's job). Carries
  `registered_as` (the DisSysLab source/sink name) and `registered_args`.
- **coordinator** — one of OfficeSpeak's four registered coordinators
  (`merge_synch`, `select`, `gate`, `record`). Carries `registered_as` (the
  OfficeSpeak name, translated by `from_officespeak.py`'s lookup table, not
  here) and `registered_args` for anything Phase 1/2 already captured (e.g.
  `record`'s initial held values, if Pat said what it starts holding).
- **transform** — office-specific; Phase 2's own English description,
  already turned into an *approved* worker per `phase3_approval.md`. Carries
  `body`, never `registered_as`.

Ports use OfficeSpeak's own Phase 1 semantic names throughout -- exactly
what Pass A/Pass B already fixed, nothing invented here.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional, Tuple

_VALID_KINDS = {"source", "sink", "transform", "coordinator"}


@dataclass(frozen=True)
class WorkerBody:
    """An approved Phase 2 implementation for one office-specific agent.

    Matches `phase3_approval.md`'s exit criteria exactly, so the generator
    never has to transform what comes out of approval -- only wrap it:

    - ``kind="python"``: ``fn`` is a **zero-arg factory** -- a callable
      that, called once per agent instantiation, returns the real
      per-message handler with the exact contract
      ``dissyslab.blocks.role.Role`` expects: ``handler(msg) -> list[(msg,
      status)]`` (or a bare message, or ``None``). This is the same shape
      every hand-written stateful role in this codebase already uses
      (``_make_ledger_fn``, ``_make_manager_fn``, the subscription-registry
      pattern) -- a fresh closure per factory call is how per-agent state
      (a running count, a pending value while awaiting a reply) stays
      private and independent across agents built from the same role. A
      genuinely stateless worker's factory just returns the same handler
      every time; nothing special is needed for that case. The generator
      wraps the result as ``Role(fn=fn(), statuses=<this agent's Phase 1
      outports, in order>)``. Order matters: ``Role`` maps ``statuses[i]``
      to the runtime port ``out_i`` positionally. ``fn`` must be defined at
      module level (not itself a runtime-built closure) so its source can
      be recovered and written to the generated role file -- see
      ``from_officespeak.py``.
    - ``kind="prompt"``: ``prompt`` is the approved prompt text, already
      containing "send to <name>" phrases in the *same order* as this
      agent's Phase 1 outports (``nl_role`` extracts ports by first
      appearance, in order). May include the ``---\\ncontract: ...\\n---``
      front matter ``load_roles_dir`` recognises; if absent, the default
      (passthrough) contract applies.
    """

    kind: str
    fn: Optional[Callable[..., Any]] = None
    prompt: Optional[str] = None

    def __post_init__(self) -> None:
        if self.kind not in ("python", "prompt"):
            raise ValueError(f"WorkerBody.kind must be 'python' or 'prompt', got {self.kind!r}")
        if self.kind == "python" and not callable(self.fn):
            raise ValueError("WorkerBody(kind='python') requires a callable fn")
        if self.kind == "prompt" and not (isinstance(self.prompt, str) and self.prompt.strip()):
            raise ValueError("WorkerBody(kind='prompt') requires a non-empty prompt")


@dataclass(frozen=True)
class AgentSpec:
    """One agent from Phase 1, in OfficeSpeak's own vocabulary.

    Parameters
    ----------
    name
        Phase 1's agent name (e.g. ``"MANAGER"``).
    kind
        One of ``"source"``, ``"sink"``, ``"transform"``, ``"coordinator"``.
    in_ports, out_ports
        Semantic port names, in Phase 1's declared order. Empty for a
        source (no inbox) or a sink (no outbox). Order is load-bearing for
        a multi-outport ``transform`` (see ``WorkerBody``).
    registered_as
        For ``source``/``sink``: the DisSysLab registered name (task #34's
        job to supply). For ``coordinator``: OfficeSpeak's own name --
        ``"merge_synch"``, ``"select"``, ``"gate"``, or ``"record"`` --
        translated to the matching DisSysLab role by
        ``from_officespeak.py``, not here. ``None`` for a ``transform``.
    registered_args
        Whatever Phase 1/2 already captured for a registered agent (e.g.
        ``{"initial": {...}}`` for a ``record`` that Pat described starting
        with something specific). Never required -- see the generator's own
        defaults (``record`` starts empty; ``select``'s command port is
        detected by name, not supplied here).
    body
        Required for ``transform``; must be ``None`` otherwise (registered
        agents need no body -- "you need not describe a registered agent;
        its behaviour is fixed").
    """

    name: str
    kind: str
    in_ports: Tuple[str, ...] = ()
    out_ports: Tuple[str, ...] = ()
    registered_as: Optional[str] = None
    registered_args: Dict[str, Any] = field(default_factory=dict)
    body: Optional[WorkerBody] = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "in_ports", tuple(self.in_ports))
        object.__setattr__(self, "out_ports", tuple(self.out_ports))
        if not isinstance(self.name, str) or not self.name:
            raise ValueError(f"AgentSpec.name must be a non-empty string, got {self.name!r}")
        if self.kind not in _VALID_KINDS:
            raise ValueError(f"AgentSpec {self.name!r}.kind must be one of {_VALID_KINDS}, got {self.kind!r}")
        if self.kind == "transform":
            if self.registered_as is not None:
                raise ValueError(f"AgentSpec {self.name!r} is a transform; transforms are office-specific, not registered")
            if self.body is None:
                raise ValueError(f"AgentSpec {self.name!r} is a transform and needs an approved body (see phase3_approval.md)")
        else:
            if self.body is not None:
                raise ValueError(f"AgentSpec {self.name!r} is a {self.kind!r}; registered agents need no body")
            if self.registered_as is None:
                raise ValueError(f"AgentSpec {self.name!r} is a {self.kind!r} and needs registered_as")


@dataclass(frozen=True)
class ConnectionSpec:
    """One 4-tuple from Phase 1: (sender, sender's outbox, receiver, receiver's inbox).

    Use ``"in_"`` for ``receiver_port`` when the receiver is an
    office-specific agent (every such agent has exactly one inbox, always
    named ``in_`` -- "a coordinator is the only kind with more than one
    inbox"); use the real semantic name for a registered coordinator's
    named inport (e.g. ``"data"``, ``"command"``, ``"val"``).
    """

    sender: str
    sender_port: str
    receiver: str
    receiver_port: str

    def __post_init__(self) -> None:
        for label, val in (("sender", self.sender), ("sender_port", self.sender_port),
                           ("receiver", self.receiver), ("receiver_port", self.receiver_port)):
            if not isinstance(val, str) or not val:
                raise ValueError(f"ConnectionSpec.{label} must be a non-empty string, got {val!r}")


@dataclass(frozen=True)
class OfficeSpeakSpec:
    """The whole office, in OfficeSpeak's own vocabulary -- the generator's input."""

    name: str
    agents: Tuple[AgentSpec, ...] = ()
    connections: Tuple[ConnectionSpec, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "agents", tuple(self.agents))
        object.__setattr__(self, "connections", tuple(self.connections))
        if not isinstance(self.name, str) or not self.name:
            raise ValueError(f"OfficeSpeakSpec.name must be a non-empty string, got {self.name!r}")
        names = [a.name for a in self.agents]
        if len(set(names)) != len(names):
            raise ValueError(f"OfficeSpeakSpec {self.name!r} has duplicate agent names: {names}")

    def agent(self, name: str) -> AgentSpec:
        for a in self.agents:
            if a.name == name:
                return a
        raise KeyError(f"OfficeSpeakSpec {self.name!r} has no agent named {name!r}")


__all__ = ["WorkerBody", "AgentSpec", "ConnectionSpec", "OfficeSpeakSpec"]
