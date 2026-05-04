"""
OfficeSpec — the in-memory shape of an office description.

An OfficeSpec is what the parser produces and what the compiler
(Layer 5) consumes. It is faithful to the user's ``office.md``: the
sections the user wrote (``Sources``, ``Sinks``, ``Agents``,
``Connections``) appear as named fields, and connection statements
are kept in their shorthand form rather than being translated to
flat edges.

The compiler's job (Layer 5) is to turn an OfficeSpec into a Layer-2
``Network``. That involves:

* materialising sources and sinks as AgentSpecs of the appropriate
  shape (sources have one outport, sinks have one inport);
* resolving each ``AgentRef`` to a full ``AgentSpec`` by reading
  the referenced office's ``office.md`` (this is the **linker**);
* translating each ConnectionStmt into one or more Edges, replacing
  user-friendly outport names like ``"copywriter"`` with the
  runtime's indexed names ``"out_0"`` / ``"out_1"`` / … in the
  order the role declared them.

That translation is intentionally out of scope here. Layer 4 stays
at the grammar level.

Closed and open offices
=======================

A **closed office** sends and receives no messages across its own
boundary: ``inputs`` and ``outputs`` are both empty. It may still
have sources and sinks of its own — the words "closed" and "open"
refer only to inter-office wiring, not to whether the office talks
to the outside world.

An **open office** declares one or more ``Inputs:`` and/or
``Outputs:``; it is meant to be embedded as a sub-office inside a
larger office. An open office may *also* have sources and sinks of
its own. Sources/sinks (world-facing) and inputs/outputs
(office-facing) are complementary, not alternatives — an open
office may carry any combination of the two.

Agents and sub-offices
======================

The ``Agents:`` section can hold two kinds of entry:

* ``Susan is an editor.``       — a leaf agent backed by a role.
* ``X is an office at <path>.`` — a sub-office.

In Layer 4 the two are represented by two types: ``AgentSpec``
(leaf, with ports already extracted from the role file) and
``AgentRef`` (sub-office, an unresolved reference to another
office on disk). Both appear together in ``OfficeSpec.agents`` —
they share an agent namespace because connection statements
reference them by bare name. Layer 4 deliberately does **not**
load the referenced office; that I/O happens at link time.

Why so many small dataclasses?
==============================

The shape mirrors the structure of office.md:

* ``OfficeSpec`` —  one per office.md
* ``SourceSpec`` —  one per entry in the ``Sources:`` line
* ``SinkSpec`` —  one per entry in the ``Sinks:`` line
* ``AgentSpec`` —  one per leaf-agent line in ``Agents:`` (Layer 3)
* ``AgentRef``  —  one per sub-office line in ``Agents:``
* ``ConnectionStmt`` —  one per line in ``Connections:``
* ``Endpoint``  —  one per end of a ConnectionStmt (source and
                    each destination)

``SourceSpec`` and ``SinkSpec`` are a near-duplicate pair (same
fields, same invariants); we keep them as separate types so the
spec mirrors the two sections the user wrote and so the compiler
can dispatch on type rather than on a string discriminator.

All types are frozen dataclasses, so OfficeSpec is hashable and
trivially safe to compare or cache.

Conventions
===========

* Args are stored as a tuple of (key, value) pairs, not a dict, so
  the spec is hashable and order-preserving. ``args`` values pass
  through ``ast.literal_eval`` at parse time so they are real Python
  literals (str, int, float, bool, None) rather than raw strings.

* ``Endpoint`` is **symmetric**: the same type appears on both ends
  of every ConnectionStmt. ``Endpoint.name`` is either an agent
  name in scope (a leaf agent, an AgentRef sub-office, a source,
  or a sink) or the literal ``"external"``; ``Endpoint.port`` is
  always a non-empty string. The parser fills in the implicit
  single inport (``IMPLICIT_INPORT``) when the user wrote a bare
  name on the destination side.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Tuple, Union

from dissyslab.office_v2.agent_spec import AgentSpec
from dissyslab.office_v2.network import EXTERNAL


# ── Source / Sink ──────────────────────────────────────────────────────


@dataclass(frozen=True)
class SourceSpec:
    """A declared source: name plus optional kw-args from the line.

    Same shape as ``SinkSpec``; kept as a separate type so the
    spec mirrors the ``Sources:`` and ``Sinks:`` sections the user
    wrote, and so the compiler can dispatch on type.

    Examples
    --------
    >>> SourceSpec(name="hacker_news", args=(("max_articles", 10),)).name
    'hacker_news'
    """

    name: str
    args: Tuple[Tuple[str, Any], ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "args", tuple(self.args))
        if not isinstance(self.name, str) or not self.name:
            raise ValueError(
                f"SourceSpec.name must be a non-empty string, got {self.name!r}"
            )
        if self.name == EXTERNAL:
            raise ValueError(
                f"SourceSpec.name cannot be {EXTERNAL!r} (reserved)"
            )
        for k, _v in self.args:
            if not isinstance(k, str) or not k:
                raise ValueError(
                    f"SourceSpec '{self.name}' has an arg with an empty key"
                )


@dataclass(frozen=True)
class SinkSpec:
    """A declared sink: name plus optional kw-args from the line.

    Same shape as ``SourceSpec``; see that class for why they are
    distinct types.
    """

    name: str
    args: Tuple[Tuple[str, Any], ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "args", tuple(self.args))
        if not isinstance(self.name, str) or not self.name:
            raise ValueError(
                f"SinkSpec.name must be a non-empty string, got {self.name!r}"
            )
        if self.name == EXTERNAL:
            raise ValueError(
                f"SinkSpec.name cannot be {EXTERNAL!r} (reserved)"
            )
        for k, _v in self.args:
            if not isinstance(k, str) or not k:
                raise ValueError(
                    f"SinkSpec '{self.name}' has an arg with an empty key"
                )


# ── AgentRef — unresolved reference to a sub-office ────────────────────


@dataclass(frozen=True)
class AgentRef:
    """A reference to an agent whose definition lives in another office.

    Used for sub-offices: the user writes
    ``X is an office at ../news_monitor.`` and Layer 4 records that
    as ``AgentRef(name="X", path="../news_monitor")``.

    Layer 4 does **not** load the referenced office — port shapes,
    nested agents, and connections are all unknown at this stage.
    Resolution is the linker's job: it reads the referenced
    ``office.md`` and replaces the AgentRef with a full AgentSpec
    whose body is the sub-office's compiled Network.

    Parameters
    ----------
    name
        The local name the surrounding office uses to talk about
        this sub-office (e.g. ``"news_monitor"``). Must be unique
        within the surrounding office's agent namespace.
    path
        The filesystem path string exactly as the user wrote it,
        relative to the office directory or absolute. The linker
        is responsible for interpreting it.
    """

    name: str
    path: str

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name:
            raise ValueError(
                f"AgentRef.name must be a non-empty string, got {self.name!r}"
            )
        if self.name == EXTERNAL:
            raise ValueError(
                f"AgentRef.name cannot be {EXTERNAL!r} (reserved)"
            )
        if not isinstance(self.path, str) or not self.path:
            raise ValueError(
                f"AgentRef '{self.name}' has empty path"
            )


# Convenience type alias for the agents tuple.
AgentEntry = Union[AgentSpec, AgentRef]


# ── Endpoint and connection statements ─────────────────────────────────


@dataclass(frozen=True)
class Endpoint:
    """One end of a connection — an (agent, port) pair.

    Endpoint is **symmetric**: the same type appears on both ends
    of every ``ConnectionStmt``. There is no separate "Sender" /
    "Recipient" distinction at the type level; the role is given
    by which side of the ConnectionStmt the Endpoint sits on.

    Parameters
    ----------
    name
        Either an agent name in scope of the surrounding office
        (a leaf agent, an ``AgentRef`` sub-office, a source, or a
        sink), or the literal ``"external"`` when this end is on
        the office boundary (i.e., one of the office's declared
        Inputs / Outputs).
    port
        A non-empty port name. For a leaf agent, the implicit
        single inport is ``IMPLICIT_INPORT`` (the parser fills it
        in when the user wrote a bare name as a destination). For
        a sub-office or ``"external"``, this is the explicit
        named port.
    """

    name: str
    port: str

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name:
            raise ValueError(
                f"Endpoint.name must be a non-empty string, got {self.name!r}"
            )
        if not isinstance(self.port, str) or not self.port:
            raise ValueError(
                f"Endpoint.port must be a non-empty string, got {self.port!r}"
            )


@dataclass(frozen=True)
class ConnectionStmt:
    """One connection statement from office.md, normalised but not translated.

    A statement translates to *one or more* edges (one per
    destination). Layer 5 does the translation; here we keep the
    statement faithful to its source-text form.

    Parameters
    ----------
    source
        The sender end of the connection. ``source.name`` is either
        an in-scope agent name (a source, leaf agent, or sub-office)
        or the literal ``"external"`` (when the line started with one
        of the office's declared inputs).
    destinations
        One or more destination ``Endpoint``s. Plural connection
        lines like ``Susan's archivist are X and Y`` produce one
        statement with two destinations.
    """

    source: Endpoint
    destinations: Tuple[Endpoint, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "destinations", tuple(self.destinations))
        if not isinstance(self.source, Endpoint):
            raise TypeError(
                f"ConnectionStmt.source must be an Endpoint, "
                f"got {type(self.source).__name__}"
            )
        if not self.destinations:
            raise ValueError(
                f"ConnectionStmt {self.source.name}.{self.source.port} has no "
                f"destinations"
            )
        for d in self.destinations:
            if not isinstance(d, Endpoint):
                raise TypeError(
                    f"ConnectionStmt.destinations must contain Endpoint "
                    f"instances, got {type(d).__name__}"
                )


# ── OfficeSpec ─────────────────────────────────────────────────────────


@dataclass(frozen=True)
class OfficeSpec:
    """The parsed, validated content of an office directory.

    Pure data — no I/O, no side effects, no recursion into other
    offices. The parser produces one of these from a single
    ``office.md`` (and its ``roles/`` directory); a later layer
    consumes one to build a runtime Network.

    Parameters
    ----------
    name
        Office name from the ``# Office: <name>`` header.
    inputs
        External inport names declared in ``Inputs:``. Empty for a
        closed office. (See class docstring for the closed/open
        distinction.)
    outputs
        External outport names declared in ``Outputs:``. Empty for a
        closed office.
    sources
        World-facing inputs declared in the ``Sources:`` section
        (RSS feeds, file readers, sockets, etc.). Independent of
        ``inputs``: a single office may have both, or either, or
        neither.
    sinks
        World-facing outputs declared in the ``Sinks:`` section
        (printers, recorders, etc.). Independent of ``outputs``.
    agents
        One entry per line in ``Agents:``. Each entry is either an
        ``AgentSpec`` (leaf agent, with ports extracted from the
        role file) or an ``AgentRef`` (sub-office, an unresolved
        reference to another office on disk). The two share one
        namespace because connection statements reference them by
        bare name.
    connections
        ``ConnectionStmt``s in source order. Layer 5 translates
        them to ``Edge``s.

    Validation performed at construction
    ------------------------------------

    * ``name`` is a non-empty string and not ``"external"``.
    * No duplicate names across sources, sinks, and agents (they
      share one namespace).
    * ``inputs`` and ``outputs`` contain non-empty strings and have
      no duplicates.
    * Every ``agents`` entry is either an ``AgentSpec`` or an
      ``AgentRef`` (frozen-dataclass type check).

    Validation NOT performed
    ------------------------

    * That every ConnectionStmt's source/destination exists. A
      later layer does this; doing it here would force the
      compiler-level error path through OfficeSpec construction.
    * That AgentRef paths point at valid office directories.
      That is the linker's responsibility; Layer 4 does no I/O
      outside the office's own directory.
    """

    name: str
    inputs: Tuple[str, ...] = ()
    outputs: Tuple[str, ...] = ()
    sources: Tuple[SourceSpec, ...] = ()
    sinks: Tuple[SinkSpec, ...] = ()
    agents: Tuple[AgentEntry, ...] = ()
    connections: Tuple[ConnectionStmt, ...] = ()

    def __post_init__(self) -> None:
        # Coerce iterables to tuples so callers may pass lists.
        object.__setattr__(self, "inputs", tuple(self.inputs))
        object.__setattr__(self, "outputs", tuple(self.outputs))
        object.__setattr__(self, "sources", tuple(self.sources))
        object.__setattr__(self, "sinks", tuple(self.sinks))
        object.__setattr__(self, "agents", tuple(self.agents))
        object.__setattr__(self, "connections", tuple(self.connections))

        if not isinstance(self.name, str) or not self.name:
            raise ValueError(
                f"OfficeSpec.name must be a non-empty string, got {self.name!r}"
            )
        if self.name == EXTERNAL:
            raise ValueError(
                f"OfficeSpec.name cannot be {EXTERNAL!r} (reserved)"
            )

        for kind, ports in (("inputs", self.inputs), ("outputs", self.outputs)):
            for p in ports:
                if not isinstance(p, str) or not p:
                    raise ValueError(
                        f"OfficeSpec.{kind} must contain non-empty strings, "
                        f"got {p!r}"
                    )
            if len(set(ports)) != len(ports):
                raise ValueError(
                    f"OfficeSpec.{kind} has duplicates: {list(ports)}"
                )

        # Every entry in agents must be an AgentSpec or AgentRef.
        for a in self.agents:
            if not isinstance(a, (AgentSpec, AgentRef)):
                raise TypeError(
                    f"OfficeSpec.agents entries must be AgentSpec or "
                    f"AgentRef, got {type(a).__name__}"
                )

        # Cross-section name uniqueness — sources, sinks, and agents share
        # one namespace because connections reference them by bare name.
        seen: dict[str, str] = {}
        for s in self.sources:
            if s.name in seen:
                raise ValueError(
                    f"name {s.name!r} declared as both {seen[s.name]} "
                    f"and a source"
                )
            seen[s.name] = "a source"
        for s in self.sinks:
            if s.name in seen:
                raise ValueError(
                    f"name {s.name!r} declared as both {seen[s.name]} "
                    f"and a sink"
                )
            seen[s.name] = "a sink"
        for a in self.agents:
            if a.name in seen:
                raise ValueError(
                    f"name {a.name!r} declared as both {seen[a.name]} "
                    f"and an agent"
                )
            seen[a.name] = "an agent"

    # ── Read-only views ────────────────────────────────────────────────

    def is_open(self) -> bool:
        """True iff this office has any external inputs or outputs."""
        return bool(self.inputs) or bool(self.outputs)

    def agent_names(self) -> Tuple[str, ...]:
        """Names of declared agents (leaf or AgentRef), in source order."""
        return tuple(a.name for a in self.agents)

    def agent_refs(self) -> Tuple[AgentRef, ...]:
        """The unresolved sub-office references in this office, in source order."""
        return tuple(a for a in self.agents if isinstance(a, AgentRef))
