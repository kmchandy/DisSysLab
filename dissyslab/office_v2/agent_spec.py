"""
AgentSpec — the wiring shape of a leaf agent in an office.

An AgentSpec carries the structural information the compiler needs to
wire an agent into a network: its name and its input / output ports.
That is all.

What AgentSpec deliberately does NOT carry
==========================================

**Implementation.** AgentSpec is pure shape. How an agent is actually
run — whether by an LLM responding to a prompt, by a built-in source/
sink class, or by a user-written Python role — is the job of
``AgentImpl`` at Layer 7. The compiler resolves a parser-level
``RoleRef`` against the role library; the library produces an
``AgentImpl`` whose ports must equal the spec's ports.

**Sub-office structure.** Sub-offices do not appear as AgentSpecs.
They appear in ``OfficeSpec.agents`` as ``RoleRef`` entries pointing
at office-roles in the library. The compiler (Layer 5) recursively
parses the referenced ``office.md`` and inlines the resulting child
``dissyslab.network.Network`` as a nested block in the parent. There
is no need for AgentSpec to model nested structure, so it doesn't.

By keeping shape and implementation separate, the compiler stays
small and the implementation lookup machinery can grow without
bloating AgentSpec.

Source / sink / transform vocabulary
====================================

The user-facing words ``Sources:``, ``Sinks:``, and the implicit
"transform" position survive only at the office.md level. Internally,
all three are AgentSpecs distinguished by port shape:

* ``in_ports == ()``         — source-shaped agent
* ``out_ports == ()``         — sink-shaped agent
* otherwise                  — transform-shaped agent

The compiler dispatches on port counts where it needs to (e.g. when
deciding whether to build a default outport edge); we do not store a
``position`` field, because it would invite drift between the field
and the actual port shape.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

from dissyslab.office_v2.office_spec_constants import EXTERNAL


@dataclass(frozen=True)
class AgentSpec:
    """The wiring shape of a leaf agent in an office.

    Parameters
    ----------
    name
        Unique identifier within the containing office. Non-empty
        string. Cannot be ``"external"`` (reserved for the network
        boundary).
    in_ports
        Ordered names of input ports. May be empty (source-shaped).
    out_ports
        Ordered names of output ports. May be empty (sink-shaped).

    Examples
    --------
    A source-shaped agent (no inports):

    >>> AgentSpec(name="rss", in_ports=(), out_ports=("out",)).name
    'rss'

    A transform-shaped agent:

    >>> spec = AgentSpec(
    ...     name="summarizer",
    ...     in_ports=("in",),
    ...     out_ports=("out",),
    ... )
    >>> spec.in_ports
    ('in',)
    """

    name: str
    in_ports: Tuple[str, ...]
    out_ports: Tuple[str, ...]

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
                f"(reserved for the network boundary)"
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
