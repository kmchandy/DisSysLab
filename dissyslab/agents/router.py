"""A router: sends each message on by the value of one field (spec section 5).

::

    agents:
        Rex: router(on="verdict")
    connections:
        Eve -> Rex
        Rex.publish -> Editor
        Rex.revise -> Writer
        Rex.otherwise -> Archive     # optional

- Every router names its field (``on=``); there is no default.
- Its outboxes are the values written after the dot. A value matches
  exactly, by its written form (``yes``, ``true``, ``3``).
- ``otherwise`` takes every value that has no outbox of its own.
- A message without the field, or with a value that has no outbox and no
  ``otherwise``, is a failure of that one message: counted, reported,
  exit non-zero. Messages are dropped only by routing them to the
  ``discard`` sink, never silently.
- The field stays in the message.

A router computes nothing (Principle 3: compute in roles, route in
routers). The decision is a field some role wrote.
"""

from __future__ import annotations

from dissyslab.agents.reply import written
from dissyslab.agents.role_agent import reject
from dissyslab.runtime.agent import Agent

OTHERWISE = "otherwise"


class RouterAgent(Agent):
    """Sends each message out of the outbox named by the value of ``on``."""

    def __init__(self, *, name: str, on: str, outboxes: list[str]) -> None:
        super().__init__(name=name, inports=["in_"], outports=list(outboxes))
        self.on = on

    def run(self) -> None:
        while True:
            msg = self.recv("in_")
            if not isinstance(msg, dict) or self.on not in msg:
                reject(self, f"the message has no field {self.on!r} to route on.")
                continue
            value = written(msg[self.on])
            if value in self.outports and value != OTHERWISE:
                self.send(msg, value)
            elif OTHERWISE in self.outports:
                self.send(msg, OTHERWISE)
            else:
                reject(
                    self,
                    f"{self.on!r} is {value!r}, which has no outbox here and there is no "
                    f"otherwise. Outboxes: {', '.join(self.outports)}.",
                )
