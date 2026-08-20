"""Alarms — the first non-reactive agent that is not a Source.

An alarm is the case the `idle` bit was introduced for: it can answer a
poll while owing a send, so "answered this round" proves nothing about
it. These tests cover the obligation accounting, the single-request
discipline, shutdown, and resume.

See docs/internals/design/termination_detection_design.md §6.
"""
from __future__ import annotations

import time

import pytest

from dissyslab import network, OfficeRunError
from dissyslab.blocks import Alarm, Sink, Source
from dissyslab.core import _TimerFired


def collect():
    got = []
    return Sink(fn=got.append), got


def one_shot(msgs):
    """A source that emits each of `msgs`, then exhausts."""
    remaining = list(msgs)
    return Source(fn=lambda: remaining.pop(0) if remaining else None)


# ── Obligation accounting ────────────────────────────────────────────────


def test_a_fresh_alarm_is_idle():
    a = Alarm(name="A")
    assert a.is_idle() is True
    assert a.is_final() is False


def test_arming_makes_it_active():
    """The whole reason the bit exists. The alarm is sitting in recv and
    would answer a poll — but it owes a send."""
    a = Alarm(name="A")
    a._arm(60.0)
    try:
        assert a.is_idle() is False
        assert a.accepted == 1 and a.discharged == 0
    finally:
        a.stop()


def test_the_worker_signals_and_never_sends(monkeypatch):
    """The rule that keeps every message event on the agent's own thread.
    The worker's only action is to put `_TimerFired` on the inbox."""
    a = Alarm(name="A")
    a.in_q["in_"] = __import__("queue").SimpleQueue()
    sent = []
    monkeypatch.setattr(a, "send", lambda msg, port: sent.append(msg))

    a._arm(0.01)
    time.sleep(0.2)

    assert sent == [], "the worker must not send"
    assert isinstance(a.in_q["in_"].get_nowait(), _TimerFired)
    assert a.discharged == 0, "discharge happens on the send, not the signal"


def test_handling_the_signal_discharges_and_sends(monkeypatch):
    a = Alarm(name="A")
    a._arm(60.0)
    a.stop()
    sent = []
    monkeypatch.setattr(a, "send", lambda msg, port: sent.append(msg))

    handled = a._handle_os_extension(_TimerFired(), "in_")

    assert handled is True
    assert a.is_idle() is True
    assert sent and sent[0]["type"] == "wake_up"
    assert sent[0]["requested"] == 60.0


def test_an_unrelated_os_message_is_not_claimed():
    """`_handle_os_extension` must fall through for anything else, or it
    would swallow messages `recv` needs to handle itself."""
    a = Alarm(name="A")
    assert a._handle_os_extension({"wake_me_in": 5}, "in_") is False


# ── The single-request discipline ────────────────────────────────────────


def test_a_second_request_is_rejected_without_touching_the_counters(monkeypatch):
    """The reason idleness is `accepted == discharged` and not the raw
    port totals: the rejection travels on the same outport, so `sent`
    advances while nothing is discharged."""
    a = Alarm(name="A")
    a._arm(60.0)
    a.stop()
    sent = []
    monkeypatch.setattr(a, "send", lambda msg, port: sent.append(msg))

    a._reject("already armed", 5)

    assert sent[0]["type"] == "alarm_error"
    assert (a.accepted, a.discharged) == (1, 0)
    assert a.is_idle() is False, "still owes the first wake-up"


@pytest.mark.parametrize(
    "request_msg",
    [
        {"wake_me_in": -1},
        {"wake_me_in": 0},
        {"wake_me_in": "soon"},
        {"wake_me_in": True},          # a bool is not a duration
        {"wrong_field": 5},
        "not a dict",
    ],
)
def test_bad_requests_produce_an_error_message(request_msg):
    """A malformed request must be reported, not silently ignored — and
    must not arm anything."""
    alarm = Alarm(name="A")
    sink, got = collect()
    g = network([(one_shot([request_msg]), alarm), (alarm, sink)])
    g.run_network(timeout=10)

    assert len(got) == 1
    assert got[0]["type"] == "alarm_error"
    assert alarm.accepted == 0


def test_a_request_over_max_wait_is_refused():
    alarm = Alarm(name="A", max_wait=2.0)
    sink, got = collect()
    g = network([(one_shot([{"wake_me_in": 9999}]), alarm), (alarm, sink)])
    g.run_network(timeout=10)

    assert got[0]["type"] == "alarm_error"
    assert "max_wait" in got[0]["error"]


# ── End to end ───────────────────────────────────────────────────────────


def test_an_alarm_fires_and_the_office_terminates():
    """The headline case: a real office, a real timer, a clean stop."""
    alarm = Alarm(name="A")
    sink, got = collect()
    g = network([(one_shot([{"wake_me_in": 0.2}]), alarm), (alarm, sink)])

    started = time.perf_counter()
    g.run_network(timeout=20)
    elapsed = time.perf_counter() - started

    assert [m["type"] for m in got] == ["wake_up"]
    assert elapsed >= 0.2, "terminated before the timer could have fired"
    assert alarm.is_idle()


def test_the_office_waits_for_a_long_timer():
    """The negative, and the assertion that would catch a wrong
    `is_idle`: the office must still be running well after every source
    has exhausted and every channel has drained.

    Written as a *terminating* office with a slow timer rather than as a
    run that hits its timeout, because a timed-out office cannot
    currently be shut down — see the note at the bottom of this file.
    """
    alarm = Alarm(name="A")
    sink, got = collect()
    g = network([(one_shot([{"wake_me_in": 0.8}]), alarm), (alarm, sink)])

    started = time.perf_counter()
    g.run_network(timeout=30)
    elapsed = time.perf_counter() - started

    # The source exhausts and the channels drain within milliseconds.
    # Everything after that is the office correctly declining to declare
    # termination while the alarm is active.
    assert elapsed >= 0.8, (
        f"office stopped after {elapsed:.2f}s — it should have waited for "
        f"the 0.8s timer, so is_idle() is reporting wrongly"
    )
    assert [m["type"] for m in got] == ["wake_up"]


def test_shutdown_releases_a_waiting_worker():
    """`Event.wait`, not `time.sleep` — otherwise Ctrl-C waits out the
    timer, and an hour-long alarm is an hour-long hang."""
    a = Alarm(name="A")
    a.in_q["in_"] = __import__("queue").SimpleQueue()
    a._arm(30.0)
    worker = a._worker

    a.stop()
    worker.join(timeout=2)

    assert not worker.is_alive(), "worker outlived the office"
    assert a.in_q["in_"].empty(), "a released worker must not signal"


# ── Snapshot and resume ──────────────────────────────────────────────────


def test_state_carries_the_outstanding_obligation():
    a = Alarm(name="A")
    a._arm(45.0)
    a.stop()

    state = a.save_state()
    assert state["accepted"] == 1
    assert state["discharged"] == 0
    assert state["pending_seconds"] == 45.0


def test_resume_re_arms_the_worker():
    """A snapshot records state, not threads. Restoring `active` without
    re-creating the means of becoming idle leaves an office that can
    never terminate — so `load_state` must start a worker."""
    restored = Alarm(name="A")
    restored.in_q["in_"] = __import__("queue").SimpleQueue()
    restored.load_state(
        {"accepted": 1, "discharged": 0, "pending_seconds": 0.1}
    )

    assert restored.is_idle() is False
    assert restored._worker is not None and restored._worker.is_alive()

    time.sleep(0.4)
    assert isinstance(restored.in_q["in_"].get_nowait(), _TimerFired), (
        "the re-armed worker never signalled"
    )
    assert restored.accepted == 1, "re-arming must not double-count"


def test_resume_with_no_obligation_starts_nothing():
    a = Alarm(name="A")
    a.load_state({"accepted": 3, "discharged": 3, "pending_seconds": None})
    assert a.is_idle() is True
    assert a._worker is None


# ── A pre-existing bug this file must work around ────────────────────────
#
# `run_network(timeout=T)` raises TimeoutError when agents are still
# running, but nothing tells those agents to stop: os_agent sends
# `_Shutdown` only when it declares termination, and the timeout path
# does not. Agent threads are created with `daemon=False`, so they stay
# blocked in `recv` forever and **the process cannot exit**.
#
# Confirmed by faulthandler: the TimeoutError is raised and printed, then
# the interpreter hangs at exit with the alarm, the sink and os_agent all
# parked in `recv`. It is not alarm-specific — any office that times out
# does this — but an alarm makes it trivial to reach, and it means a test
# cannot assert "this office should not terminate" by running it to a
# timeout.
#
# The fix is small: send `_Shutdown` to every agent on the timeout path
# before raising, so the office stops the same way it would on a clean
# termination. Not done here because it changes `Network.run` for every
# caller and belongs in its own change.
