"""A sink whose front matter declares ``in:``: each message is checked first.

A sink is where an office acts -- it sends mail, posts, books a sale --
so it is the place a precondition matters most. A sink written in the
office's ``sinks/`` folder may declare ``in:`` in its front matter, with
the same contracts a role uses (``price (number, >= 1000)``). Every
message is checked on arrival, before the sink's ``__call__``; one that
does not fit is not acted on. It is counted, the first is printed, the
run summary reports it, and ``dsl run`` exits non-zero: the same rule as
a role's ``in:`` (:mod:`dissyslab.agents.role_agent`).

Without ``in:`` the sink is an ordinary ``Sink``. Built-in sinks have no
front matter yet, so they are not checked here.
"""

from __future__ import annotations

from typing import Any, Callable

from dissyslab.agents.reply import check_incoming
from dissyslab.agents.role_agent import reject
from dissyslab.blocks.sink import Sink
from dissyslab.office.frontmatter import FrontMatter


class CheckedSink(Sink):
    """A ``Sink`` that checks each message against ``in:`` before acting."""

    def __init__(self, *, fn: Callable[..., Any], name: str, front_matter: FrontMatter) -> None:
        super().__init__(fn=fn, name=name)
        self.front_matter = front_matter

    def run(self) -> None:
        while True:
            msg = self.recv("in_")
            if not isinstance(msg, dict):
                reject(self, f"it received a {type(msg).__name__}; every message is a JSON object.")
                continue
            problem = check_incoming(msg, self.front_matter)
            if problem:
                reject(self, f"the message it received does not fit its in: line: {problem}")
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
