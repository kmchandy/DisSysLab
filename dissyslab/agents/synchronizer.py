"""The keyed synchronizer (spec section 6).

::

    agents:
        Sync: synchronizer(on="url")
    connections:
        Eve -> Sync.entities
        Sam -> Sync.severity
        Sync -> Riley

Its inboxes are the names its connections use (``entities``,
``severity``). For each value of the key field ``on``, it keeps one
group. When a message with that key has arrived on **every** inbox, the
group is complete: the messages are merged into one and sent, and the
group is forgotten, so the same key may come again later.

**Merging.** A field carried by two messages with the same value is not a
conflict (parallel annotators each receive a copy of the same item, so
its original fields agree). The same field with different values is a
failure of that group, naming the field and the two inboxes; the
framework never chooses.

**The collected form**, ``synchronizer(on="span", collect="results")``,
for many identical workers: nothing is merged. The message sent is the
key plus one field, here ``results``, mapping each inbox name to the
message that arrived on it.

**Why a key and not position.** If one branch drops a message (a role's
reply did not fit), a synchronizer that pairs the k-th message of each
inbox merges different items from then on. With a key, the dropped
message leaves one group incomplete and every other group is unaffected.
Incomplete groups are reported when the run ends, and make ``dsl run``
exit non-zero. The key must be unique among items in progress at the
same time.

**How it runs.** Like the framework's fan-in agent (``MergeAsynch``), it
has one thread per inbox, so it takes each message as soon as it
arrives, from whichever inbox; the threads share the group table under
one lock.
"""

from __future__ import annotations

import sys
import threading
from typing import Any

from dissyslab.agents.reply import Message, written
from dissyslab.agents.role_agent import reject
from dissyslab.runtime.agent import Agent
from dissyslab.runtime.messages import _ShutdownSignal


class SynchronizerAgent(Agent):
    """Groups messages by key across its inboxes; sends each complete group."""

    def __init__(
        self, *, name: str, on: str, inboxes: list[str], collect: str | None = None
    ) -> None:
        super().__init__(name=name, inports=list(inboxes), outports=["out_"])
        self.on = on
        self.collect = collect
        #: key -> {inbox: message}, for groups still waiting for an inbox.
        self.groups: dict[str, dict[str, Message]] = {}
        self._lock = threading.Lock()
        # Several threads share the operating system's bookkeeping too, as
        # in MergeAsynch, so its no-op lock must be a real one here.
        self._snapshot_lock = threading.Lock()

    # ── Receiving ──────────────────────────────────────────────────────────

    def run(self) -> None:
        threads = [
            threading.Thread(target=self._worker, args=(inbox,), name=f"{self.name}:{inbox}")
            for inbox in self.inports
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

    def _worker(self, inbox: str) -> None:
        try:
            while True:
                self._arrive(inbox, self.recv(inbox))
        except _ShutdownSignal:
            pass  # the termination detector has ended the run

    def _arrive(self, inbox: str, msg: Any) -> None:
        if not isinstance(msg, dict) or self.on not in msg:
            reject(self, f"a message on {inbox} has no field {self.on!r} to synchronize on.")
            return
        key = written(msg[self.on])
        with self._lock:
            group = self.groups.setdefault(key, {})
            if inbox in group:
                reject(
                    self,
                    f"a second message with {self.on}={key} arrived on {inbox} before its "
                    "group was complete; the key must be unique among items in progress.",
                )
                return
            group[inbox] = msg
            if len(group) < len(self.inports):
                return
            del self.groups[key]
            out = self._combine(key, group)
            if out is not None:
                self.send(out, "out_")

    # ── Combining ──────────────────────────────────────────────────────────

    def _combine(self, key: str, group: dict[str, Message]) -> Message | None:
        """The message for a complete group, or None (reported) on a conflict."""
        if self.collect is not None:
            return {self.on: group[self.inports[0]][self.on], self.collect: dict(group)}
        merged: Message = {}
        source: dict[str, str] = {}  # field -> the inbox it first came from
        for inbox in self.inports:
            for field, value in group[inbox].items():
                if field in merged and merged[field] != value:
                    reject(
                        self,
                        f"in group {self.on}={key}, {field!r} differs between "
                        f"{source[field]} and {inbox}; the framework never chooses.",
                    )
                    return None
                merged.setdefault(field, value)
                source.setdefault(field, inbox)
        return merged

    # ── At the end of the run ──────────────────────────────────────────────

    def incomplete(self) -> list[str]:
        """One line per group still waiting: its key and the inboxes it lacks."""
        lines = []
        for key, group in self.groups.items():
            missing = [i for i in self.inports if i not in group]
            lines.append(f"group {self.on}={key} is missing {', '.join(missing)}")
        return lines

    def shutdown(self) -> None:
        """Report every incomplete group; each counts as a failure (exit non-zero)."""
        lines = self.incomplete()
        for line in lines:
            self.record_failure(line)
        if lines:
            sys.stderr.write(
                f"\n[{self.name}] {len(lines)} incomplete group(s) at the end of the run:\n"
                + "".join(f"  {line}\n" for line in lines)
            )
            sys.stderr.flush()
