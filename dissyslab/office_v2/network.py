"""
Network — the declared wiring of an office.

A Network is a list of Edges plus the external inports and outports
that the network exposes to the outside world. It is the wiring as the
student wrote it down in ``office.md``, before the runtime inserts
any merge or broadcast agents.

Relationship to ``dissyslab.network.Network`` (the runtime core)
================================================================

These are different layers:

* ``dissyslab.network.Network`` is the *runtime* network. It owns
  agents, queues, threads, and a compile pipeline that inserts
  Broadcast / MergeAsynch agents to maintain the 1-to-1 invariant.
  The compiler in Layer 5 hands one of these to the runtime to be
  executed.

* ``dissyslab.office_v2.Network`` (this file) is the *spec*. It is
  pure data: edges, declared external ports. No agents, no queues,
  no compile step. It says what the office should be wired like; it
  does not run anything.

The two share the convention that the literal string ``"external"``
is a reserved node identity meaning "this network's boundary". An
Edge with ``from_agent="external"`` enters the network through one
of its inports; an Edge with ``to_agent="external"`` leaves through
one of its outports.

Design choices
==============

* **Frozen dataclass.** Networks are values: hashable, comparable,
  trivially safe to use as cache keys or memoize over.

* **Edges stored as a tuple.** Tuples are hashable; lists are not.
  ``__post_init__`` coerces, so callers may pass either; what is
  stored is always immutable.

* **Validation in ``__post_init__``.** Building a malformed Network
  is always a bug — better to fail at construction. Validation is
  local: it does not consult any agent registry. Agent existence is
  a higher-layer concern.

* **Loops are allowed.** Existing gallery offices use them; the
  runtime supports them; we add no cycle check.

* **Fan-in is allowed.** Multiple Edges sharing
  ``(to_agent, to_port)`` are legal at this layer. The runtime's
  ``_insert_fanout_fanin`` will introduce merge agents at compile
  time. We do not try to anticipate that here.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import FrozenSet, Tuple

from dissyslab.office_v2.edge import Edge


# Reserved node identity for "this network's boundary". Mirrors the
# convention in dissyslab.network.Network. Compilers and parsers
# should import this constant rather than spell the string inline.
EXTERNAL = "external"


@dataclass(frozen=True)
class Network:
    """The declared wiring of an office: edges + external port surface.

    Parameters
    ----------
    edges
        Iterable of ``Edge`` instances. Stored as a tuple.
    inports
        Names of external inports this network exposes. Each declared
        inport must be referenced by at least one Edge with
        ``from_agent == "external"`` and matching ``from_port``.
    outports
        Names of external outports this network exposes. Each declared
        outport must be referenced by at least one Edge with
        ``to_agent == "external"`` and matching ``to_port``.

    Examples
    --------
    A closed network with two agents and a sink:

    >>> n = Network(edges=(
    ...     Edge("rss", "out", "summarizer", "in"),
    ...     Edge("summarizer", "out", "printer", "in"),
    ... ))
    >>> sorted(n.agents())
    ['printer', 'rss', 'summarizer']
    >>> n.is_open()
    False

    An open network exposing an external inport:

    >>> n = Network(
    ...     edges=(Edge("external", "feed", "summarizer", "in"),),
    ...     inports=("feed",),
    ... )
    >>> n.is_open()
    True
    >>> n.out_edges("summarizer")
    ()
    """

    edges: Tuple[Edge, ...]
    inports: Tuple[str, ...] = ()
    outports: Tuple[str, ...] = ()

    def __post_init__(self) -> None:
        # Coerce iterables to tuples so callers may pass lists.
        # frozen=True forbids assignment; object.__setattr__ is the
        # documented escape hatch for __post_init__ normalisation.
        object.__setattr__(self, "edges", tuple(self.edges))
        object.__setattr__(self, "inports", tuple(self.inports))
        object.__setattr__(self, "outports", tuple(self.outports))

        for e in self.edges:
            if not isinstance(e, Edge):
                raise TypeError(
                    f"Network.edges must contain Edge instances, "
                    f"got {type(e).__name__}: {e!r}"
                )
        for p in self.inports:
            if not isinstance(p, str) or not p:
                raise ValueError(
                    f"Network.inports must contain non-empty strings, "
                    f"got {p!r}"
                )
        for p in self.outports:
            if not isinstance(p, str) or not p:
                raise ValueError(
                    f"Network.outports must contain non-empty strings, "
                    f"got {p!r}"
                )

        self.validate()

    # ── Read-only views ────────────────────────────────────────────────

    def agents(self) -> FrozenSet[str]:
        """Names of all agents referenced by edges, excluding "external"."""
        names = set()
        for e in self.edges:
            if e.from_agent != EXTERNAL:
                names.add(e.from_agent)
            if e.to_agent != EXTERNAL:
                names.add(e.to_agent)
        return frozenset(names)

    def is_open(self) -> bool:
        """True iff this network has any external inports or outports."""
        return bool(self.inports) or bool(self.outports)

    def out_edges(self, agent: str) -> Tuple[Edge, ...]:
        """All edges leaving ``agent`` (i.e. with from_agent == agent)."""
        return tuple(e for e in self.edges if e.from_agent == agent)

    def in_edges(self, agent: str) -> Tuple[Edge, ...]:
        """All edges entering ``agent`` (i.e. with to_agent == agent)."""
        return tuple(e for e in self.edges if e.to_agent == agent)

    # ── Validation ─────────────────────────────────────────────────────

    def validate(self) -> None:
        """Check structural invariants. Raises ValueError on failure.

        Checks performed:

        * No duplicate names in ``inports`` or ``outports``.
        * Every declared external inport is referenced by at least one
          Edge with ``from_agent == "external"`` and matching
          ``from_port``.
        * Every declared external outport is referenced by at least
          one Edge with ``to_agent == "external"`` and matching
          ``to_port``.
        * Every Edge that touches the boundary uses a declared port —
          catches typos like saying ``from_port="fed"`` when the
          inport is named ``"feed"``.

        Checks intentionally NOT performed:

        * Agent existence — Network has no agent registry; that is
          Layer 3+ territory.
        * Cycle freedom — loops are legal; gallery examples use them.
        * Single-source-per-inport — multi-source fan-in is legal
          here; the runtime inserts merge agents at compile time.
        """
        if len(set(self.inports)) != len(self.inports):
            raise ValueError(
                f"Network has duplicate inport names: {list(self.inports)}"
            )
        if len(set(self.outports)) != len(self.outports):
            raise ValueError(
                f"Network has duplicate outport names: {list(self.outports)}"
            )

        ext_in_ports_used = {
            e.from_port for e in self.edges if e.from_agent == EXTERNAL
        }
        for p in self.inports:
            if p not in ext_in_ports_used:
                raise ValueError(
                    f"Network external inport '{p}' is declared but not "
                    f"connected to any agent. Add an Edge with "
                    f"from_agent='external', from_port='{p}'."
                )

        ext_out_ports_used = {
            e.to_port for e in self.edges if e.to_agent == EXTERNAL
        }
        for p in self.outports:
            if p not in ext_out_ports_used:
                raise ValueError(
                    f"Network external outport '{p}' is declared but not "
                    f"connected from any agent. Add an Edge with "
                    f"to_agent='external', to_port='{p}'."
                )

        for e in self.edges:
            if e.from_agent == EXTERNAL and e.from_port not in self.inports:
                raise ValueError(
                    f"Edge {e} uses external inport '{e.from_port}' "
                    f"which is not declared in Network.inports "
                    f"{list(self.inports)}."
                )
            if e.to_agent == EXTERNAL and e.to_port not in self.outports:
                raise ValueError(
                    f"Edge {e} uses external outport '{e.to_port}' "
                    f"which is not declared in Network.outports "
                    f"{list(self.outports)}."
                )
