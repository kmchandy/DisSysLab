"""What an office file says, as data.

The parser (:mod:`dissyslab.office.syntax`) turns the text of an
``office.md`` written in the line form of the spec
(``docs/internals/design/officespeak_revised.md``, section 3.1) into an
``OfficeFile``. Nothing here knows which kinds exist or what ports they
have; that is for the checks and the builder. This is only what the file
says, with the line each statement came from, so every later error can
point at a line.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

#: The sections an office file may have, in the order they usually appear.
SECTIONS = ("inputs", "outputs", "sources", "sinks", "agents", "connections")

#: The port a connection uses when it names none.
DEFAULT_OUTBOX = "out"
DEFAULT_INBOX = "in"


@dataclass(frozen=True)
class Declaration:
    """One ``name: kind(arg=value, ...)`` line.

    ``section`` is ``"sources"``, ``"sinks"`` or ``"agents"``. ``args``
    holds the arguments as Python values (strings, numbers, booleans,
    lists, dicts). For ``kind(...)`` or a bare ``kind`` with no name, the
    name is the kind.
    """

    name: str
    kind: str
    args: dict[str, Any]
    section: str
    line: int


@dataclass(frozen=True)
class PortRef:
    """One end of a connection: ``name`` or ``name.port``.

    ``port`` is None when the line names no port; the default (``out`` at
    the sending end, ``in`` at the receiving end) is applied by
    ``Connection.out_port`` and ``Connection.in_port``.
    """

    name: str
    port: str | None = None

    def __str__(self) -> str:
        return self.name if self.port is None else f"{self.name}.{self.port}"


@dataclass(frozen=True)
class Connection:
    """One arrow: messages from ``sender`` go to ``receiver``.

    A line such as ``a, b -> c -> d, e`` gives several of these, one per
    pair of neighbouring names, each with the same ``line``.
    """

    sender: PortRef
    receiver: PortRef
    line: int

    @property
    def out_port(self) -> str:
        """The sender's outbox, ``out`` unless the line named one."""
        return self.sender.port or DEFAULT_OUTBOX

    @property
    def in_port(self) -> str:
        """The receiver's inbox, ``in`` unless the line named one."""
        return self.receiver.port or DEFAULT_INBOX

    def __str__(self) -> str:
        return f"{self.sender} -> {self.receiver}"


@dataclass(frozen=True)
class OfficeFile:
    """Everything an office file says, in the order it says it."""

    inputs: tuple[str, ...] = ()
    outputs: tuple[str, ...] = ()
    sources: tuple[Declaration, ...] = ()
    sinks: tuple[Declaration, ...] = ()
    agents: tuple[Declaration, ...] = ()
    connections: tuple[Connection, ...] = ()
    #: For each name the file declares, the line it was declared on.
    names: dict[str, int] = field(default_factory=dict)

    @property
    def declarations(self) -> tuple[Declaration, ...]:
        """Sources, sinks and agents together."""
        return self.sources + self.sinks + self.agents

    def inboxes_of(self, name: str) -> list[str]:
        """The inboxes the connections use on ``name``, in first-use order.

        For a synchronizer these *are* its inboxes (spec section 3.3).
        """
        seen: list[str] = []
        for c in self.connections:
            if c.receiver.name == name and c.in_port not in seen:
                seen.append(c.in_port)
        return seen
