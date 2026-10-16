"""The running agent for a role: an annotator (a map) or an author (a flat-map).

Every role in an office, English or Python, runs as one of two agents:

- ``AnnotatorAgent``: for each message, call the role, check its reply,
  add the reply's fields to the message, send that one message on;
- ``AuthorAgent``: for each message, call the role, check its reply,
  send each object of the reply as a new message (none, one, or many).

What a role *is* -- a prompt sent to a model, or a Python object -- is
given to the agent as ``call``, a function from one message to the
role's raw reply (see :mod:`dissyslab.agents.english` and
:mod:`dissyslab.agents.python_role`). The agent does not know or care
which. The checks are in :mod:`dissyslab.agents.reply`.

A message that cannot be handled -- the role raised, or its reply does
not fit its front matter -- costs that one message: it is counted, the
first one is printed, the run summary reports them, and ``dsl run``
exits non-zero (spec 4.5). Fields a reply carries without declaring
them are dropped and counted per field name; the run summary lists them
as a note.
"""

from __future__ import annotations

import sys
from abc import abstractmethod
from typing import Any, Callable

from dissyslab.agents.reply import (
    Accepted,
    Message,
    Rejected,
    Result,
    check_annotator_reply,
    check_author_reply,
)
from dissyslab.office.frontmatter import FrontMatter
from dissyslab.runtime.agent import Agent

#: A role, as the agent sees it: one message in, the raw reply out.
Call = Callable[[Message], Any]


class RoleAgent(Agent):
    """What both kinds share: receive, call the role, check, count, send."""

    def __init__(self, *, name: str, call: Call, front_matter: FrontMatter) -> None:
        super().__init__(name=name, inports=["in_"], outports=["out_"])
        self.call = call
        self.front_matter = front_matter
        #: Undeclared field name -> how many replies carried it.
        self.dropped_fields: dict[str, int] = {}

    @abstractmethod
    def check(self, reply: Any, incoming: Message) -> Result:
        """Check the role's reply; return the messages to send, or why not."""

    def run(self) -> None:
        while True:
            msg = self.recv("in_")
            if not isinstance(msg, dict):
                self._reject(f"it received a {type(msg).__name__}; every message is a JSON object.")
                continue
            try:
                reply = self.call(msg)
            except Exception as exc:  # the role's own failure costs this message only
                self.report_failure(exc, doing="its role")
                continue
            result = self.check(reply, msg)
            if isinstance(result, Rejected):
                self._reject(f"its reply does not fit its front matter: {result.reason}")
                continue
            self._count_dropped(result)
            for out in result.messages:
                self.send(out, "out_")

    def _count_dropped(self, result: Accepted) -> None:
        for field in result.dropped:
            self.dropped_fields[field] = self.dropped_fields.get(field, 0) + 1

    def _reject(self, reason: str) -> None:
        """Count a message the role could not handle; print the first one."""
        first = self.first_failure is None
        self.record_failure(reason)
        if first:
            sys.stderr.write(
                f"\n[{self.name}] {reason}\n"
                f"This message was not processed. The office carries on; "
                f"the run summary counts the rest.\n\n"
            )
            sys.stderr.flush()


class AnnotatorAgent(RoleAgent):
    """A map: one message in, the same message with the role's fields added out."""

    def check(self, reply: Any, incoming: Message) -> Result:
        return check_annotator_reply(reply, self.front_matter, incoming)


class AuthorAgent(RoleAgent):
    """A flat-map: one message in, each object of the role's reply out."""

    def check(self, reply: Any, incoming: Message) -> Result:
        return check_author_reply(reply, self.front_matter)


def role_agent(name: str, call: Call, front_matter: FrontMatter) -> RoleAgent:
    """The agent for a role of either kind, chosen by its ``kind:``."""
    cls = AuthorAgent if front_matter.is_author else AnnotatorAgent
    return cls(name=name, call=call, front_matter=front_matter)
