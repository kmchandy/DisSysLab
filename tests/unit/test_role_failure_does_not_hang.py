"""A role that fails must not take the office down with it.

The failure this pins was the worst one in the framework, and it was
found by writing `1 / 0` in a role while probing something else.

``Role.run`` ended with::

    except Exception as e:
        print(f"[Role '{self.name}'] Error in fn: {e}")
        print(traceback.format_exc())
        return

The ``return`` ends the thread. The agent never reaches the shutdown
protocol, termination detection never completes, and **the office runs
for ever** -- for any exception at all, in any role. A first-year's
``1 / 0`` produced a program that never stopped, having printed the
reason into a stream of other agents' output, spliced mid-line because
threads share one stdout.

`dsl check` said "no problems", correctly: it is a runtime fact.

What makes this file worth its runtime is that every assertion here
fails by *hanging* against the old code, so each one needs a timeout
rather than an ``assert``. A unit test asserting on ``Role.run``'s
internals would not have caught it -- the check was already there and
the message was already good. It was what happened *after* the message
that was wrong, and that is only visible from outside the process.
"""
from __future__ import annotations

import json
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest


ROLE_PY = '''\
"""
---
inboxes: in_
outboxes: keep, discard
---
"""
from dissyslab.office.library import AgentRoleEntry
from dissyslab.blocks.role import Role

def _fn(msg):
    n = msg.get("n", 0) if isinstance(msg, dict) else 0
    {body}
    return [(msg, "keep" if n % 2 == 0 else "discard")]

role = AgentRoleEntry(
    name="splitter", in_ports=("in_",), out_ports=("keep", "discard"),
    factory=lambda: Role(fn=_fn, statuses=["keep", "discard"]),
)
'''

OFFICE_MD = """\
# Office: probe

Sources: file_source(filepath="items.jsonl")
Sinks: console_printer, discard

Agents:
Split is a splitter.

Connections:
file_source's destination is Split.
Split's keep is console_printer.
Split's discard is discard.
"""


def _office(tmp_path: Path, body: str) -> Path:
    d = tmp_path / "probe"
    (d / "roles").mkdir(parents=True)
    (d / "office.md").write_text(OFFICE_MD, encoding="utf-8")
    (d / "roles" / "splitter.py").write_text(
        ROLE_PY.format(body=body), encoding="utf-8"
    )
    (d / "items.jsonl").write_text(
        "".join(json.dumps({"n": i}) + "\n" for i in range(1, 6)),
        encoding="utf-8",
    )
    return d


def _run(office: Path, seconds: int = 60):
    """Run the office in a subprocess with a hard timeout.

    A subprocess and not an in-process call: the failure is a thread
    that never ends, and there is no way to assert "this did not hang"
    from inside the process it hung.
    """
    try:
        return subprocess.run(
            [sys.executable, "-m", "dissyslab.cli", "run", str(office)],
            capture_output=True, text=True, timeout=seconds,
        )
    except subprocess.TimeoutExpired:
        pytest.fail(
            f"the office did not finish within {seconds}s -- this is the "
            "hang: a role failed, its thread ended, and termination "
            "detection waited for an agent that was gone."
        )


@pytest.mark.timeout(180)
def test_an_ordinary_python_bug_does_not_hang_the_office(tmp_path):
    """`1 / 0` in a role. The mistake a first-year actually makes."""
    result = _run(_office(tmp_path, "if n == 3:\n        1 / 0"))
    assert result.returncode != 0, (
        "an office where an agent could not do its work must not report "
        "success:\n" + result.stdout
    )


@pytest.mark.timeout(180)
def test_the_other_four_messages_are_still_processed(tmp_path):
    """One bad message costs that message, not the agent.

    Five items in, one of them fails. The remaining four must come out
    the other side -- otherwise "record and continue" would just be a
    quieter way to lose the run.
    """
    office = _office(tmp_path, "if n == 3:\n        1 / 0")
    result = _run(office)
    # n=2 and n=4 go to console_printer; n=1 and n=5 to discard.
    assert "{'n': 2}" in result.stdout and "{'n': 4}" in result.stdout
    assert "received      5" in result.stdout, (
        "the agent stopped reading:\n" + result.stdout
    )


@pytest.mark.timeout(180)
def test_the_summary_counts_the_failure_and_quotes_the_first(tmp_path):
    """Where a person actually looks. The traceback goes to stderr and
    scrolls; the summary is the last thing on screen."""
    result = _run(_office(tmp_path, "if n == 3:\n        1 / 0"))
    assert "failed      1" in result.stdout
    assert "failed on 1 message(s)" in result.stdout
    assert "ZeroDivisionError" in result.stdout, (
        "the summary must quote the first failure, not just count it"
    )


@pytest.mark.timeout(180)
def test_the_traceback_names_the_student_s_own_file(tmp_path):
    """Not a line inside the framework. The point of the report is that
    she can go and look at what she wrote."""
    result = _run(_office(tmp_path, "if n == 3:\n        1 / 0"))
    assert "splitter.py" in result.stderr
    assert "ZeroDivisionError" in result.stderr


@pytest.mark.timeout(180)
def test_the_report_goes_to_stderr_not_into_the_output(tmp_path):
    """Two threads sharing stdout produced

        ...division by zero[1] {'n': 2}

    -- the message spliced into another agent's output mid-line. The
    report is one write, on stderr, so redirecting the office's output
    to a file still leaves the failure on the terminal.
    """
    result = _run(_office(tmp_path, "if n == 3:\n        1 / 0"))
    assert "Traceback" not in result.stdout
    assert "Traceback" in result.stderr


@pytest.mark.timeout(180)
def test_a_clean_office_still_exits_zero(tmp_path):
    """The other half. A guard that fires on a healthy run is worse
    than no guard, because the exit code is what a script reads."""
    result = _run(_office(tmp_path, "pass"))
    assert result.returncode == 0, result.stdout + result.stderr
    assert "failed" not in result.stdout


# ── the same defect, in the four blocks the first fix missed ──────────
#
# `Role.run` was fixed and reported as "the hang is fixed". It was not:
# `Transform`, `Sink`, `Split` and `Coordinator` each carried their own
# copy of
#
#     except Exception as e:
#         print(...)
#         print(traceback.format_exc())
#         return
#
# -- four more copies of the same four lines, and therefore four more
# copies of the same hang. A sink meeting a full disk still stopped
# everything. Found a week later, while checking whether a backtest
# role could hang, by asking which classes those roles actually build.
#
# The behaviour now lives once, in `Agent.report_failure`, and these
# tests exercise every caller. A shared implementation is what stops
# this recurring; a test per caller is what proves the sharing is real.

import pytest as _pytest

from dissyslab import network as _network
from dissyslab.blocks import (
    Coordinator as _Coordinator,
    Sink as _Sink,
    Source as _Source,
    Split as _Split,
    Transform as _Transform,
)


def _source(items, **kw):
    data, i = list(items), [0]

    def fn():
        if i[0] >= len(data):
            return None
        i[0] += 1
        return data[i[0] - 1]

    return _Source(fn=fn, **kw)


@_pytest.mark.timeout(60)
def test_a_transform_that_raises_does_not_hang():
    got = []
    def boom(m):
        if m == 3:
            raise ValueError("boom")
        return m

    t = _Transform(fn=boom, name="T")
    g = _network([(_source([1, 2, 3, 4, 5], name="s"), t),
                  (t, _Sink(fn=got.append, name="k"))])
    code = g.run_network(timeout=None)
    assert code == 1, "an agent that failed must not report success"
    assert got == [1, 2, 4, 5], "one bad message costs that message only"


@_pytest.mark.timeout(60)
def test_a_sink_that_raises_does_not_hang():
    """A full disk, a bad path, a record the writer chokes on. The
    office used to stop dead and never exit."""
    seen = []
    def boom(m):
        seen.append(m)
        if m == 3:
            raise IOError("No space left on device")

    g = _network([(_source([1, 2, 3, 4, 5], name="s"),
                   _Sink(fn=boom, name="recorder"))])
    code = g.run_network(timeout=None)
    assert code == 1
    assert seen == [1, 2, 3, 4, 5], "the sink kept receiving after the failure"


@_pytest.mark.timeout(60)
def test_a_split_that_raises_does_not_hang():
    a, b = [], []
    def boom(m):
        if m == 3:
            raise ValueError("boom")
        return [m, m]

    sp = _Split(fn=boom, num_outputs=2, name="S")
    g = _network([(_source([1, 2, 3, 4, 5], name="s"), sp),
                  (sp.out_0, _Sink(fn=a.append, name="a")),
                  (sp.out_1, _Sink(fn=b.append, name="b"))])
    code = g.run_network(timeout=None)
    assert code == 1
    assert a == [1, 2, 4, 5] and b == [1, 2, 4, 5]


@_pytest.mark.timeout(60)
def test_the_failure_is_counted_and_quoted_once_per_agent():
    """Whichever block failed, the run summary answers the same two
    questions: how many, and what was the first one."""
    def boom(m):
        raise ValueError(f"boom on {m}")

    g = _network([(_source([1, 2, 3], name="s"),
                   _Sink(fn=boom, name="recorder"))])
    g.run_network(timeout=None)
    report = g.run_report()
    name = next(n for n in report["agents"] if n.endswith("recorder"))
    assert report["agents"][name]["failures"] == 3
    failed = dict((n, d) for n, _c, d in report["failed_agents"])
    assert "ValueError: boom on 1" in failed[name], failed
