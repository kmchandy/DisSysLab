"""
AgentSpec — the wiring shape of an agent in an office.

An AgentSpec carries the structural information the compiler needs
to wire an agent into a network: name, input ports, output ports,
and (if the agent is itself a composed sub-network) its body.

What AgentSpec deliberately does NOT carry
==========================================

Implementation. AgentSpec is pure shape. How an agent is actually
run — whether by an LLM responding to a prompt, by a registered
Python class, or by a user-written Python function — is the job of
AgentImpl at Layer 7.

Why the split? Because shape and implementation are two questions
that the compiler resolves at different times:

* The compiler (Layer 5) wires edges between ports. It needs only
  shapes — which agents exist, what ports they expose. It does
  not need to know how any of them will run.
* The AgentImpl factory (Layer 7) takes an AgentSpec and produces
  a runnable callable. It looks up the implementation by name —
  first against a built-in registry, then against the office's
  own roles directory (md for NL, py for Python), then against
  dotted-path imports. Local definitions win over built-ins on
  name collisions, so students can override.

By keeping these two concerns in separate types, the compiler stays
small and the implementation lookup machinery can grow without
bloating AgentSpec.

The three position categories
=============================

The vocabulary "source / sink / transform" is preserved for the
user (office.md still has those sections). Internally these are
just three different port shapes of the same AgentSpec type:

    Source      — no inports, >=1 outport
    Sink        — >=1 inport, no outport
    Transform   — >=1 inport, >=1 outport

The ``position`` property derives this label from port counts so
code that wants to ask can ask. We do not store position as a
field — that would invite drift between the field and the actual
shape.

Open offices as first-class agents
==================================

The body field is what makes open offices first-class agents. An
open office is an AgentSpec whose body is a Network of further
agents, with the Network's external inports/outports matching the
AgentSpec's own ports. The compiler treats it identically to a
leaf agent for wiring purposes — composability with no special
case code.

When body is not None we enforce, in __post_init__, that
``body.inports == in_ports`` and ``body.outports == out_ports``.
Catching this mismatch at construction is much friendlier than
discovering it deep inside the compiler.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

from dissyslab.office_v2.network import EXTERNAL, Network


@dataclass(frozen=True)
class AgentSpec:
    """The wiring shape of an agent in an office.

    Parameters
    ----------
    name
        Unique identifier within the containing office. Non-empty
        string. Cannot be ``"external"`` (reserved by Network as
        the boundary marker).
    in_ports
        Ordered names of input ports. May be empty (source).
    out_ports
        Ordered names of output ports. May be empty (sink).
    body
        If this agent is composed of further agents, the Network
        wiring them. ``None`` for leaf agents. When non-``None``,
        ``body.inports`` must equal ``in_ports`` and
        ``body.outports`` must equal ``out_ports``.

    Examples
    --------
    A source:

    >>> AgentSpec(name="rss", in_ports=(), out_ports=("out",)).position
    'source'

    A transform:

    >>> AgentSpec(
    ...     name="summarizer", in_ports=("in",), out_ports=("out",)
    ... ).position
    'transform'

    A sub-office (composed agent) — body wires further agents:

    >>> from dissyslab.office_v2 import Network, Edge
    >>> body = Network(
    ...     edges=(
    ...         Edge("external", "in", "filter", "in"),
    ...         Edge("filter", "out", "external", "out"),
    ...     ),
    ...     inports=("in",),
    ...     outports=("out",),
    ... )
    >>> spec = AgentSpec(
    ...     name="news_filter",
    ...     in_ports=("in",),
    ...     out_ports=("out",),
    ...     body=body,
    ... )
    >>> spec.is_leaf
    False
    >>> spec.position
    'transform'
    """

    name: str
    in_ports: Tuple[str, ...]
    out_ports: Tuple[str, ...]
    body: Optional[Network] = None

    def __post_init__(self) -> None:
        # Coerce iterables to tuples so callers may pass lists.
        object.__setattr__(self, "in_ports", tuple(self.in_ports))
        object.__setattr__(self, "out_ports", tuple(self.out_ports))

        if not isinstance(self.name, str) or not self.name:
            raise ValueError(
                f"AgentSpec.name must be a non-empty string, got {self.name!r}"
            )
        if self.name == EXTERNAL:
            raise ValueError(
                f"AgentSpec.name cannot be {EXTERNAL!r} "
                f"(reserved by Network for boundary edges)"
            )

        for p in self.in_ports:
            if not isinstance(p, str) or not p:
                raise ValueError(
                    f"AgentSpec '{self.name}' in_ports must contain "
                    f"non-empty strings, got {p!r}"
                )
        for p in self.out_ports:
            if not isinstance(p, str) or not p:
                raise ValueError(
                    f"AgentSpec '{self.name}' out_ports must contain "
                    f"non-empty strings, got {p!r}"
                )

        if len(set(self.in_ports)) != len(self.in_ports):
            raise ValueError(
                f"AgentSpec '{self.name}' has duplicate in_ports: "
                f"{list(self.in_ports)}"
            )
        if len(set(self.out_ports)) != len(self.out_ports):
            raise ValueError(
                f"AgentSpec '{self.name}' has duplicate out_ports: "
                f"{list(self.out_ports)}"
            )

        if not self.in_ports and not self.out_ports:
            raise ValueError(
                f"AgentSpec '{self.name}' has no ports at all; an agent "
                f"must have at least one inport or one outport"
            )

        if self.body is not None:
            if not isinstance(self.body, Network):
                raise TypeError(
                    f"AgentSpec '{self.name}' body must be Network or None, "
                    f"got {type(self.body).__name__}"
                )
            if self.body.inports != self.in_ports:
                raise ValueError(
                    f"AgentSpec '{self.name}' body.inports "
                    f"{list(self.body.inports)} does not match in_ports "
                    f"{list(self.in_ports)}"
                )
            if self.body.outports != self.out_ports:
                raise ValueError(
                    f"AgentSpec '{self.name}' body.outports "
                    f"{list(self.body.outports)} does not match out_ports "
                    f"{list(self.out_ports)}"
                )

    @property
    def is_leaf(self) -> bool:
        """True iff this agent has no body (will be filled by AgentImpl)."""
        return self.body is None

    @property
    def position(self) -> str:
        """One of 'source', 'sink', or 'transform', derived from port shape."""
        if not self.in_ports:
            return "source"
        if not self.out_ports:
            return "sink"
        return "transform"
