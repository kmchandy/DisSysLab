"""Sinks, and the two things that can stop a sink acting.

A sink is where an office acts -- it sends mail, posts, books a sale --
so it is the place a precondition matters most.

A sink written in the office's ``sinks/`` folder may declare ``in:`` in
its front matter, with the same contracts a role uses
(``price (number, >= 1000)``). Every message is checked on arrival,
before the sink's ``__call__``. One that does not fit is a refusal: the
sink does not act on it, nor on anything after it, and the office stops
and records it (:mod:`dissyslab.agents.refusals`).

Another agent's refusal does not stop a sink: what reaches a sink after
a stop is work that had already passed every role, and every contract,
before the stop (no role sends anything once the office is stopping).
Built-in sinks have no front matter yet, so they have no contract of
their own.
"""

from __future__ import annotations

from typing import Any, Callable

from dissyslab.agents.refusals import Refusals
from dissyslab.agents.reply import check_incoming
from dissyslab.agents.role_agent import reject
from dissyslab.blocks.sink import Sink
from dissyslab.office.frontmatter import FrontMatter


class CheckedSink(Sink):
    """A ``Sink`` that checks each message against ``in:`` before acting."""

    def __init__(self, *, fn: Callable[..., Any], name: str, front_matter: FrontMatter) -> None:
        super().__init__(fn=fn, name=name)
        self.front_matter = front_matter
        #: Shared by the run (set by ``dsl run``); None: a refusal costs one message.
        self.refusals: Refusals | None = None
        #: True once this sink has refused a message: it acts on nothing more.
        self.stopped = False

    def _refuse(self, reason: str, msg: Any) -> None:
        if self.refusals is None:
            reject(self, reason)
        else:
            self.stopped = True
            self.refusals.refuse(self, reason, msg)

    def run(self) -> None:
        while True:
            msg = self.recv("in_")
            if self.stopped:
                continue  # it refused a message: it acts on nothing more
            if not isinstance(msg, dict):
                self._refuse(f"it received a {type(msg).__name__}; every message is a JSON object.",
                             msg)
                continue
            problem = check_incoming(msg, self.front_matter)
            if problem:
                self._refuse(f"the message it received does not fit its in: line: {problem}", msg)
                continue
            try:
                self._fn(msg)
            except Exception as exc:  # the sink's own failure costs this message only
                self.report_failure(exc, doing="writing its output")


def sink_agent(*, fn: Callable[..., Any], name: str, front_matter: FrontMatter) -> Sink:
    """A ``CheckedSink`` if the front matter declares ``in:``, else a plain ``Sink``."""
    if front_matter.input_fields is None:
        return Sink(fn=fn, name=name)
    return CheckedSink(fn=fn, name=name, front_matter=front_matter)


