"""A timed-out office has to stop, not just say it timed out.

`run(timeout=T)` raised `TimeoutError` and told nobody: `os_agent`
sends `_Shutdown` only when it *declares termination*, and a timeout is
exactly the case where it did not. Agent threads are `daemon=False`, so
they stayed parked in `recv` and the interpreter could not exit — the
timeout was printed, and then the program hung. A student meets that in
the first hour and concludes Ctrl-C is broken.

Confirmed originally with faulthandler; see the note at the foot of
`tests/unit/test_alarm.py`, which had to work around it.

These tests run inside the test process, so they cannot assert "the
interpreter exits". They assert the operational proxy: after the
`TimeoutError`, no non-daemon agent thread is still alive.
"""
from __future__ import annotations

import threading
import time

import pytest

from dissyslab import network
from dissyslab.blocks import Sink, Source, Transform


def _forever_source():
    """A source that keeps producing, the way a poller does. Nothing
    here will ever declare termination, which is the situation being
    tested."""
    def fn():
        time.sleep(0.01)
        return "tick"
    return Source(fn=fn, name="src")


def _hanging_network():
    mid = Transform(fn=lambda x: x, name="mid")
    return network([
        (_forever_source(), mid),
        (mid, Sink(fn=lambda x: None, name="out")),
    ])


def _alive(net) -> list[str]:
    live = {t.name for t in threading.enumerate() if t.is_alive()}
    return sorted(t.name for t in net.threads if t.name in live)


def _settle(net, seconds: float = 3.0) -> list[str]:
    deadline = time.time() + seconds
    while time.time() < deadline and _alive(net):
        time.sleep(0.05)
    return _alive(net)


def test_a_timed_out_office_stops_its_agents():
    """The whole bug in one assertion."""
    net = _hanging_network()
    with pytest.raises(TimeoutError):
        net.run_network(timeout=1.0)

    assert _settle(net) == [], (
        "agents were still running after the timeout. They are "
        "daemon=False, so the process cannot exit and the office looks "
        "as though Ctrl-C is broken."
    )


def test_the_timeout_is_still_reported():
    """Stopping the agents must not swallow the error. A timeout is
    still a fault; it just should not also hang."""
    net = _hanging_network()
    with pytest.raises(TimeoutError) as exc:
        net.run_network(timeout=1.0)
    assert "timed out" in str(exc.value).lower()
    _settle(net)


def test_stopping_an_already_stopped_network_reports_nothing_left():
    """`_stop_all_agents` returns the threads still alive rather than a
    bool, which is what lets `run` distinguish "all stopped" from "one
    is asleep between polls and cannot notice yet"."""
    net = _hanging_network()
    with pytest.raises(TimeoutError):
        net.run_network(timeout=1.0)
    _settle(net)
    assert net._stop_all_agents(grace=0.2) == []


def test_a_normal_office_still_terminates_by_itself():
    """The fix fires only on the timeout path. An office that finishes
    must still finish the way it always did — by os_agent declaring
    termination, not by anyone being told to stop."""
    seen = []
    items = iter(["a", "b", "c"])

    def fn():
        return next(items, None)

    net = network([(Source(fn=fn, name="src"), Sink(fn=seen.append, name="out"))])
    net.run_network(timeout=10)
    assert seen == ["a", "b", "c"]
    assert _alive(net) == []
