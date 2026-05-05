"""
OfficeSpec — the in-memory shape of an office description.

An OfficeSpec is what the parser produces and what the compiler
(Layer 5) consumes. It is faithful to the user's ``office.md``: the
sections the user wrote (``Sources``, ``Sinks``, ``Agents``,
``Connections``) appear as named fields, and connection statements
are kept in their shorthand form rather than being translated to
flat edges.

The compiler's job (Layer 5) is to turn an OfficeSpec into a runtime
``dissyslab.network.Network``. That involves:

* materialising sources and sinks as runtime agents from library
  factories;
* resolving each ``RoleRef`` against the role library — an
  ``AgentRoleEntry`` becomes a leaf ``Agent``, an ``OfficeRoleEntry``
  triggers recursive parsing of the referenced ``office.md``;
* translating each ConnectionStmt into one or more 4-tuple edges,
  replacing user-friendly outport names like ``"copywriter"`` with
  the runtime's indexed names ``"out_0"`` / ``"out_1"`` / … in the
  order the library entry declared them.

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

In Layer 4 both are represented uniformly as ``RoleRef``: a pair
of ``(agent_name, role_name)`` plus an optional ``path`` set only
when the user wrote the inline ``office at <path>`` form. The
library tells the compiler whether a given ``role_name`` resolves
to a leaf agent or a sub-office; the parser does no I/O outside
the office's own ``office.md``.

Why so many small dataclasses?
==============================

The shape mirrors the structure of office.md:

* ``OfficeSpec`` —  one per office.md
* ``SourceSpec`` —  one per entry in the ``Sources:`` line
* ``SinkSpec`` —  one per entry in the ``Sinks:`` line
* ``RoleRef``   —  one per line in ``Agents:`` (leaf or sub-office)
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
from typing import Any, Optional, Tuple

from dissyslab.office_v2.agent_spec import AgentSpec
from dissyslab.office_v2.office_spec_constants import EXTERNAL


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


# ── RoleRef — uniform reference to a role in the library ──────────────


@dataclass(frozen=True)
class RoleRef:
    """A reference from an office.md to a role in the library.

    The parser produces one ``RoleRef`` per ``Agents:`` line. Both
    leaf agents (``Susan is an editor.``) and sub-offices
    (``news_monitor is an office at ../news_monitor.``) share this
    type — the library decides what each reference resolves to.

    Parameters
    ----------
    agent_name
        The local name the surrounding office uses (e.g. ``"Susan"``,
        ``"news_monitor"``). Unique within the office's agent
        namespace; cannot be ``"external"``.
    role_name
        The role's identifier in the library (e.g. ``"editor"``,
        ``"news_monitor"``). The library lookup tells the compiler
        whether this is an ``AgentRoleEntry`` (leaf) or an
        ``OfficeRoleEntry`` (sub-office).
    path
        Optional filesystem hint, only set when the user wrote
        ``office at <path>`` inline in office.md. Layer 5 uses it as
        a transitional sugar: if the library has no entry for
        ``role_name`` and ``path`` is set, the compiler auto-registers
        an ``OfficeRoleEntry`` on the fly. The long-run direction is
        explicit library entries; in the meantime this keeps the
        gallery's ``Offices:`` syntax working.

    Notes
    -----
    Layer 4 (the parser) does **no** library lookup — it simply
    records the name. Validation that the role exists is the
    compiler's job at link time.
    """

    agent_name: str
    role_name: str
    path: Optional[str] = None

    def __post_init__(self) -> None:
        if not isinstance(self.agent_name, str) or not self.agent_name:
            raise ValueError(
                f"RoleRef.agent_name must be a non-empty string, "
                f"got {self.agent_name!r}"
            )
        if self.agent_name == EXTERNAL:
            raise ValueError(
                f"RoleRef.agent_name cannot be {EXTERNAL!r} (reserved)"
            )
        if not isinstance(self.role_name, str) or not self.role_name:
            raise ValueError(
                f"RoleRef {self.agent_name!r} has empty role_name"
            )
        if self.path is not None and (
            not isinstance(self.path, str) or not self.path
        ):
            raise ValueError(
                f"RoleRef {self.agent_name!r} has empty path "
                f"(use path=None to indicate no path)"
            )

    # Convenience accessor — many callers used to read AgentRef.name;
    # keep a `name` property so error formatting and call-sites that
    # iterate over OfficeSpec.agents still work without sprinkling
    # ``.agent_name`` everywhere.
    @property
    def name(self) -> str:
        """Alias for ``agent_name`` — the in-office identifier."""
        return self.agent_name


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
        One entry per line in ``Agents:``. Every entry is a
        uniform ``RoleRef``; whether it resolves to a leaf agent or
        to a sub-office is decided at link time by the library
        lookup. Connection statements reference these entries by
        their ``agent_name``.
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
    agents: Tuple[RoleRef, ...] = ()
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

        # Every entry in agents must be a RoleRef. Layer 4's parser
        # produces only RoleRefs; the runtime port shape is the
        # library's job, not OfficeSpec's.
        for a in self.agents:
            if not isinstance(a, RoleRef):
                raise TypeError(
                    f"OfficeSpec.agents entries must be RoleRef, "
                    f"got {type(a).__name__}"
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
        """Names of declared agents in source order (the in-office names)."""
        return tuple(a.agent_name for a in self.agents)

    def office_refs(self) -> Tuple[RoleRef, ...]:
        """RoleRefs that point at sub-offices on disk, in source order.

        A RoleRef counts as an "office ref" iff its ``path`` was
        captured from inline ``office at <path>`` syntax. RoleRefs
        without a path are leaf-role references (resolved entirely
        through the library).
        """
        return tuple(a for a in self.agents if a.path is not None)
