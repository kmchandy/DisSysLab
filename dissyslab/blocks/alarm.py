# dissyslab/blocks/alarm.py

"""
Alarm: wake an agent up later.

An agent is **reactive** — it acts only when a message arrives. That is
the property the whole termination argument rests on: a message can only
appear via a send, every send is caused by a receive, and the recursion
bottoms out at a source. An agent that could send after a `sleep()` would
break it, silently, by adding a second way to send without receiving.

So DisSysLab has no `sleep`. An agent that wants to be woken later asks
an Alarm, and waits for the answer like it waits for anything else:

    Agents:
    Watcher is a poller.
    Watcher_alarm is an alarm.

    Connections:
    Watcher's timer is Watcher_alarm.
    Watcher_alarm's out is Watcher.

`Watcher` sends `{"wake_me_in": 30}` and carries on. Thirty seconds
later a message arrives on its inbox like any other. Nothing in the
office had to learn about time.

Private, and one timer at a time
================================

An alarm belongs to exactly one agent: the only edge in is from `X`, the
only edge out is to `X`. That makes routing trivial — there is only one
place a wake-up can go — and it means an alarm never has to identify
*whose* timer fired.

**One outstanding request.** A second request while a timer is armed is
an error, reported as ``{"type": "alarm_error", ...}`` on the outport,
which the run summary counts and surfaces. Allowing more brings
cancellation, reordering and per-request identity with it, and there is
no use case yet that needs them.

Why a worker thread
===================

On accepting a request the alarm spawns a thread that waits. The alarm's
own loop stays in ``recv``, so it keeps answering polls, snapshot markers
and shutdown throughout — an alarm set for an hour still answers a
snapshot query ten minutes in.

**The worker never sends.** It waits, then puts one ``_TimerFired`` on
the alarm's own inbox, and stops. The alarm's main loop does the sending.
Two reasons, and the second is the serious one: the counters would
otherwise be written from one thread and read from another, and
Chandy–Lamport requires a process to record its state atomically with
respect to its own send and receive events. A worker sending while the
main thread composes a snapshot reply could record "I have not sent" for
a message the receiver has already taken as pre-cut — an inconsistent
cut, and on recovery a message lost or duplicated.

The alternative — a ``recv`` with a timeout instead of a thread — works
and was rejected. It hears OS messages during the wait perfectly well
(measured: a poll sent 0.2 s into a 10 s wait was received after
0.200 s). But it inherits an obligation: **the deadline is absolute, the
timeout is relative.** ``recv`` loops after handling an OS message, and
re-waiting the full interval each time means every poll resets the alarm.
Measured with polls every 0.3 s and a 1 s alarm, the naive version never
fires at all. "Signal, don't send" can be stated once and checked by
inspection; deadline arithmetic must be got right every time the loop is
touched.

Termination
===========

The alarm is **non-reactive**: it can answer a poll while owing a send,
so answering proves nothing and it must report its own activity.

    idle  ⟺  accepted == discharged

Equivalently, and this is the framing to keep: *the alarm is idle iff it
has not yet received the finished message from its worker.* Idleness
depends only on messages the alarm has handled, never on the worker's
internal state — which is what makes it snapshottable.

Not the raw port totals. The rejected-request error travels on the same
outport, so ``sent`` would advance without discharging anything and the
alarm would read idle with a timer still pending.

Because ``discharged`` advances *with the send*, there is no instant at
which the alarm reads idle while owing a message. The obligation is
covered at every point either by the counter inequality or by an
unbalanced channel, and the handover between them is one event.

Snapshot and resume
===================

There is no race between ``_TimerFired`` and a snapshot query: both
arrive on the same queue, and the alarm's own processing of them defines
the order. Either the query comes first and the alarm correctly reports
active, or ``_TimerFired`` comes first, the wake-up goes out, and it
correctly reports idle. (That argument needs the single inport. With
two, a marker on one and ``_TimerFired`` on the other would need the
full channel-state machinery to order.)

Resume is where the care is needed. A snapshot records state, not
threads. Restore ``{active, accepted=1, discharged=0}`` and the alarm is
active with nothing alive to make it idle again — permanently. So the
snapshotted state carries the outstanding timer, and resume re-arms the
worker. It re-arms for the **full** interval: the remainder is not a
quantity the system can honestly claim to know, since logical time does
not survive a checkpoint.

See docs/internals/design/termination_detection_design.md §6.
"""

from __future__ import annotations

import threading
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from dissyslab.core import Agent, _TimerFired


class Alarm(Agent):
    """One agent's private alarm clock.

    Args:
        name:       agent name, as usual.
        max_wait:   an upper bound in seconds on any accepted interval,
                    default 3600. A student who asks for 10 000 seconds
                    has almost always made an arithmetic mistake, and an
                    office that will not stop for three hours is
                    indistinguishable from one that has hung.

    Message in — on ``in_``, from its owner::

        {"wake_me_in": 30}          # seconds

    Message out — on ``out_``, to its owner::

        {"type": "wake_up", "requested": 30, "at": "2026-08-19T…"}

    or, if a request arrives while a timer is already armed::

        {"type": "alarm_error", "error": "…", "requested": 5}
    """

    REQUEST_FIELD = "wake_me_in"

    def __init__(
        self,
        *,
        name: Optional[str] = None,
        max_wait: float = 3600.0,
    ):
        super().__init__(name=name, inports=["in_"], outports=["out_"])

        if max_wait <= 0:
            raise ValueError(f"max_wait must be positive, got {max_wait!r}")
        self.max_wait = float(max_wait)

        # Obligation counters. `accepted` advances when a timer is armed,
        # `discharged` when the wake-up is sent. Not the port totals —
        # see the module docstring.
        self.accepted: int = 0
        self.discharged: int = 0

        # The interval of the armed timer, kept so a resumed alarm can
        # re-arm. None means no timer.
        self.pending_seconds: Optional[float] = None

        # Set at shutdown so a waiting worker returns at once instead of
        # holding the office open for the rest of its interval.
        self._stop = threading.Event()
        self._worker: Optional[threading.Thread] = None

    # ── Activity ──────────────────────────────────────────────────────

    def is_idle(self) -> bool:
        """Idle iff every accepted timer has been discharged.

        Read at reply time from two counters, each advanced by the event
        it names, so there is no window in which this disagrees with
        reality. A flag set separately would have one, between the timer
        firing and the message going out.
        """
        return self.accepted == self.discharged

    # ── The worker ────────────────────────────────────────────────────

    def _arm(self, seconds: float) -> None:
        """Start the wait. The worker signals; it never sends."""
        self.accepted += 1
        self.pending_seconds = seconds

        def wait_then_signal() -> None:
            # Event.wait rather than time.sleep, so shutdown does not
            # have to wait out the interval.
            if self._stop.wait(timeout=seconds):
                return                      # shutting down; send nothing
            q = self.in_q.get("in_")
            if q is not None:
                q.put(_TimerFired())

        self._worker = threading.Thread(
            target=wait_then_signal,
            name=f"{self.name or 'alarm'}_worker",
            daemon=True,
        )
        self._worker.start()

    def stop(self) -> None:
        """Release a waiting worker. Called on shutdown."""
        self._stop.set()

    # ── Message handling ──────────────────────────────────────────────

    def _handle_os_extension(self, msg: Any, inport: str) -> bool:
        """Catch the worker's signal and send the wake-up.

        This runs inside ``recv``, on the alarm's own thread, which is
        what keeps every message event on one thread.
        """
        if not isinstance(msg, _TimerFired):
            return False

        requested = self.pending_seconds
        self.pending_seconds = None
        self.send(
            {
                "type": "wake_up",
                "requested": requested,
                "at": datetime.now(timezone.utc).isoformat(),
            },
            "out_",
        )
        self.discharged += 1
        return True

    def _reject(self, reason: str, requested: Any) -> None:
        self.send(
            {
                "type": "alarm_error",
                "error": reason,
                "requested": requested,
                "at": datetime.now(timezone.utc).isoformat(),
            },
            "out_",
        )

    def run(self) -> None:
        """Wait for a request; arm a timer; repeat.

        The wake-up itself is sent from ``_handle_os_extension``, not
        from here — this loop is only ever blocked in ``recv``, which is
        what lets it answer polls and snapshot markers while a timer runs.
        """
        while True:
            msg = self.recv("in_")

            requested = (
                msg.get(self.REQUEST_FIELD) if isinstance(msg, dict) else None
            )

            if not isinstance(requested, (int, float)) or isinstance(
                requested, bool
            ):
                self._reject(
                    f"an alarm expects {{'{self.REQUEST_FIELD}': <seconds>}}; "
                    f"got {msg!r}",
                    requested,
                )
                continue

            if requested <= 0:
                self._reject(
                    f"{self.REQUEST_FIELD} must be positive, got {requested!r}",
                    requested,
                )
                continue

            if requested > self.max_wait:
                self._reject(
                    f"{self.REQUEST_FIELD}={requested} exceeds max_wait="
                    f"{self.max_wait}. An office that will not stop for that "
                    f"long is indistinguishable from one that has hung; raise "
                    f"max_wait deliberately if you mean it.",
                    requested,
                )
                continue

            if not self.is_idle():
                # One timer at a time. Neither counter advances, so the
                # alarm stays correctly active for the timer already armed.
                self._reject(
                    f"a timer is already armed for {self.pending_seconds}s; "
                    f"an alarm holds one request at a time",
                    requested,
                )
                continue

            self._arm(float(requested))

    # ── Snapshot ──────────────────────────────────────────────────────

    def save_state(self) -> Dict[str, Any]:
        """State for a snapshot.

        The obligation must be here, because a snapshot records state and
        not threads: restoring `active` without the means of becoming
        idle again leaves an office that can never terminate.
        """
        return {
            "accepted": self.accepted,
            "discharged": self.discharged,
            "pending_seconds": self.pending_seconds,
        }

    def load_state(self, state: Dict[str, Any]) -> None:
        """Restore, and re-arm a timer that was outstanding at the cut.

        Re-arms for the **full** interval. The remainder would need the
        elapsed time to have survived the checkpoint, and it does not;
        claiming to know it would be worse than being plainly
        conservative.
        """
        self.accepted = int(state.get("accepted", 0))
        self.discharged = int(state.get("discharged", 0))
        pending = state.get("pending_seconds")

        if self.accepted > self.discharged and pending:
            # Re-arm without advancing `accepted` — the obligation was
            # already counted before the snapshot.
            self.accepted -= 1
            self._arm(float(pending))
        else:
            self.pending_seconds = None
