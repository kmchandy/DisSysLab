"""A contract refusal stops the whole office, and is recorded.

A message that does not fit an agent's ``in:``, or a reply that does not
fit its ``out:``, may be an attack: a customer talking a model into a
one-dollar car, a web page with instructions hidden in it. So the office
does not carry on as if nothing happened. The first refusal:

1. is printed, with the agent and the reason;
2. is written, with the message (and the reply, if there was one), to
   ``refused.jsonl`` in the office's folder;
3. stops the office, as a cut at that moment: sources stop; no role runs
   again, so no model is called and no role sends anything; the agent
   that refused acts on nothing more. Work that had already passed every
   role before the stop -- and so every contract on its way -- still
   reaches its sinks, so what a stopped office has written does not
   depend on thread timing. The run summary is printed and ``dsl run``
   exits non-zero.

An office can say otherwise for one agent by wiring its ``refused``
outbox: ``Sal.refused -> Sorry -> screen``. Then a refusal at Sal goes
out of that outbox -- the message Sal received, with a field ``refusal``
giving the reason -- and the office carries on. It is still recorded
in ``refused.jsonl``, and the run summary counts it. What should happen
to a refusal is then a design decision written in the network, where
``dsl check`` and ``dsl draw`` can see it.

A Python role that raises is not a refusal: that is a bug in the role,
and it costs only that message, as before.

``Refusals`` is shared by every agent in one run. Agents built without
one (unit tests that build an agent by hand) report a refusal the old
way, as a failure of that one message.
"""

from __future__ import annotations

import json
import sys
import threading
from pathlib import Path
from typing import Any, Callable

from dissyslab.runtime.agent import Agent

#: The file, in the office's folder, that holds every refusal of a run.
RECORD = "refused.jsonl"

_NO_REPLY = object()


def _name(agent: Agent) -> str:
    """The agent's name as a string (``Agent.name`` is typed optional)."""
    return agent.name if agent.name is not None else type(agent).__name__


class Refusals:
    """The refusals of one run, and the stop they cause."""

    def __init__(self, record: Path | None, stop: Callable[[], Any]) -> None:
        self.record = record
        self._stop = stop
        self._lock = threading.Lock()
        self._halted = threading.Event()
        #: (agent name, reason) of the first refusal that stopped the office, or None.
        self.first: tuple[str, str] | None = None
        #: Agent name -> refusals it sent to its ``refused`` outbox.
        self.routed: dict[str, int] = {}
        if record is not None and record.exists():
            record.unlink()  # a record from an earlier run would mislead

    def halted(self) -> bool:
        """True once any agent has refused a message: act on nothing more."""
        return self._halted.is_set()

    def _write(self, entry: dict[str, Any]) -> None:
        if self.record is not None:
            with open(self.record, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, default=str) + "\n")

    def route(self, agent: Agent, reason: str, message: Any, reply: Any = _NO_REPLY) -> None:
        """A refusal the office sends to ``Name.refused``: record it; do not stop.

        The office has said what a refusal there should do, so it carries on.
        The first such refusal of each agent is printed; the run summary
        counts them all.
        """
        name = _name(agent)
        entry: dict[str, Any] = {"agent": name, "reason": reason, "message": message,
                                 "sent_to": f"{name}.refused"}
        if reply is not _NO_REPLY:
            entry["reply"] = reply
        with self._lock:
            first = name not in self.routed
            self.routed[name] = self.routed.get(name, 0) + 1
            self._write(entry)
        if first:
            where = f" It is recorded in {RECORD}." if self.record is not None else ""
            short = name.rsplit("::", 1)[-1]
            sys.stderr.write(
                f"\n[{name}] {reason}\n"
                f"A contract refused this message; it went to {short}.refused, and the "
                f"office carries on.{where}\n\n"
            )
            sys.stderr.flush()

    def refuse(self, agent: Agent, reason: str, message: Any, reply: Any = _NO_REPLY) -> None:
        """Count, record and print the refusal; on the first, stop the office."""
        agent.record_failure(reason)
        name = _name(agent)
        entry: dict[str, Any] = {"agent": name, "reason": reason, "message": message}
        if reply is not _NO_REPLY:
            entry["reply"] = reply
        with self._lock:
            first = self.first is None
            if first:
                self.first = (name, reason)
            self._write(entry)
            self._halted.set()
        if first:
            where = f" It is recorded in {RECORD}." if self.record is not None else ""
            sys.stderr.write(
                f"\n[{name}] {reason}\n"
                f"A contract refused this message, so the office is stopping.{where}\n\n"
            )
            sys.stderr.flush()
            # Not from this thread's own call stack: the stop waits on nothing,
            # but it must not run inside the agent that is still unwinding.
            threading.Thread(target=self._stop, name="refusal_stop", daemon=True).start()
