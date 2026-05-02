"""
Edge — the on-wire representation of a connection in a DisSysLab network.

An Edge is the smallest unit of network wiring: it says "messages
emitted from `from_agent` on `from_port` are delivered to `to_agent`
on `to_port`." A whole network is just a list of Edges.

Design choices (ratified for v2):

* **Plain strings, not typed wrappers.** Agent and port names are
  strings. We do not introduce AgentName / PortName newtypes. The
  cost (extra vocabulary for first-year students) is not worth the
  benefit (catching a class of typo that the validator already
  catches at network-build time).

* **Always explicit, never implicit.** Both ports are always present.
  There are no string sentinels like the v1 ``"destination"`` marker
  for the single output port of a source, and no ``"discard"`` magic
  string in the recipient list. If a stream needs to be thrown away,
  it connects to a real sink agent whose job is discarding.

* **Pure data — no behaviour beyond being printable and comparable.**
  Frozen dataclass so Edges are hashable and trivially safe to put in
  sets, use as dict keys, and reason about as values.

The ``__post_init__`` check is intentionally cheap: it catches the
common mistake of accidentally passing ``None`` or an empty string
(e.g. from a misparse) but does not try to validate that the agents
or ports actually exist. That is a network-level concern; an Edge in
isolation cannot know what is "valid".
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Edge:
    """A directed connection from ``from_agent.from_port`` to ``to_agent.to_port``.

    All four fields are non-empty strings. Edges are immutable and
    hashable; two Edges compare equal iff all four fields are equal.

    Examples
    --------
    >>> e = Edge("rss_feed", "out", "summarizer", "in")
    >>> str(e)
    'rss_feed.out -> summarizer.in'
    >>> e == Edge("rss_feed", "out", "summarizer", "in")
    True
    """

    from_agent: str
    from_port: str
    to_agent: str
    to_port: str

    def __post_init__(self) -> None:
        for field in ("from_agent", "from_port", "to_agent", "to_port"):
            value = getattr(self, field)
            if not isinstance(value, str) or not value:
                raise ValueError(
                    f"Edge.{field} must be a non-empty string, "
                    f"got {value!r}"
                )

    def __str__(self) -> str:
        return (
            f"{self.from_agent}.{self.from_port} "
            f"-> {self.to_agent}.{self.to_port}"
        )
