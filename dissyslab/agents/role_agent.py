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

A message that does not fit the role's ``in:`` (checked before the role
is called, so a model never sees it), or a reply that does not fit its
``out:``, is a **refusal**: it stops the whole office and is recorded
(:mod:`dissyslab.agents.refusals`). A role that raises costs only that
one message: it is counted, the first one is printed, the run summary
reports them, and ``dsl run`` exits non-zero (spec 4.5). Fields a reply
carries without declaring them are dropped and counted per field name;
the run summary lists them as a note.
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
    check_incoming,
)
from dissyslab.agents.refusals import Refusals
from dissyslab.office.frontmatter import FrontMatter
from dissyslab.runtime.agent import Agent

#: A role, as the agent sees it: one message in, the raw reply out.
Call = Callable[[Message], Any]

#: The outbox a refusal goes to when the office wires ``Name.refused``.
REFUSED = "refused"


class RoleAgent(Agent):
    """What both kinds share: receive, call the role, check, count, send."""

    def __init__(self, *, name: str, call: Call, front_matter: FrontMatter,
                 refused_outbox: bool = False) -> None:
        super().__init__(name=name, inports=["in_"],
                         outports=["out_", REFUSED] if refused_outbox else ["out_"])
        self.call = call
        self.front_matter = front_matter
        #: True when the office wires ``Name.refused``: a refusal goes there, and
        #: the office carries on, instead of stopping.
        self.refused_outbox = refused_outbox
        #: Undeclared field name -> how many replies carried it.
        self.dropped_fields: dict[str, int] = {}
        #: Shared by the run (set by ``dsl run``); None: a refusal costs one message.
        self.refusals: Refusals | None = None

    @abstractmethod
    def check(self, reply: Any, incoming: Message) -> Result:
        """Check the role's reply; return the messages to send, or why not."""

    def run(self) -> None:
        while True:
            msg = self.recv("in_")
            if self.refusals is not None and self.refusals.halted():
                continue  # the office is stopping: no model call, no reply
            if not isinstance(msg, dict):
                self._refuse(f"it received a {type(msg).__name__}; every message is a JSON object.",
                             msg)
                continue
            problem = check_incoming(msg, self.front_matter)
            if problem:
                self._refuse(f"the message it received does not fit its in: line: {problem}", msg)
                continue
            try:
                reply = self.call(msg)
            except Exception as exc:  # the role's own failure costs this message only
                self.report_failure(exc, doing="its role")
                continue
            result = self.check(reply, msg)
            if isinstance(result, Rejected):
                self._refuse(f"its reply does not fit its front matter: {result.reason}",
                             msg, reply)
                continue
            if self.refusals is not None and self.refusals.halted():
                continue  # stopped while this reply was being made: send nothing
            self._count_dropped(result)
            for out in result.messages:
                self.send(out, "out_")

    def _count_dropped(self, result: Accepted) -> None:
        for field in result.dropped:
            self.dropped_fields[field] = self.dropped_fields.get(field, 0) + 1

    def _refuse(self, reason: str, msg: Any, *reply: Any) -> None:
        if self.refused_outbox:
            # The office has said what to do with a refusal: send it on, with
            # the reason, and carry on. It is still recorded.
            if self.refusals is not None:
                self.refusals.route(self, reason, msg, *reply)
            refused = {**msg, "refusal": reason} if isinstance(msg, dict) else \
                {"message": msg, "refusal": reason}
            self.send(refused, REFUSED)
        elif self.refusals is None:
            reject(self, reason)
        else:
            self.refusals.refuse(self, reason, msg, *reply)


def reject(agent: Agent, reason: str) -> None:
    """Count a message an agent could not handle; print only the first one.

    The same rule as ``Agent.report_failure``, for a failure that is a
    sentence rather than an exception: counted, the first printed to
    stderr as one write, the rest left to the run summary.
    """
    first = agent.first_failure is None
    agent.record_failure(reason)
    if first:
        sys.stderr.write(
            f"\n[{agent.name}] {reason}\n"
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


def role_agent(name: str, call: Call, front_matter: FrontMatter,
               refused_outbox: bool = False) -> RoleAgent:
    """The agent for a role of either kind, chosen by its ``kind:``."""
    cls = AuthorAgent if front_matter.is_author else AnnotatorAgent
    return cls(name=name, call=call, front_matter=front_matter, refused_outbox=refused_outbox)
