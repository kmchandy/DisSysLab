# tests/unit/test_periodic_brief_html_sink.py
"""
Regression tests for the periodic_brief HTML sink's terminal output.

These cover the subtle bug behind #147.9: the dissyslab framework's
network shutdown only invokes ``agent.shutdown()`` on Sink BLOCKS,
not on the underlying instance the Sink wraps. We rely on an
``atexit`` hook registered in ``__init__`` so the brief actually
prints at process exit. If that wiring breaks, ``dsl run
periodic_brief`` silently reverts to "writes brief.html only" — a
regression an HN visitor would notice immediately.

We test the atexit path with a subprocess (the most honest reproduction
of the real lifecycle: instantiate, feed messages, let the interpreter
exit, capture what fired during shutdown). We also test the
non-atexit path (explicit ``finalize()``) for completeness.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from io import StringIO
from textwrap import dedent

import pytest

from dissyslab.gallery.apps.periodic_brief.sinks.periodic_brief_html_sink import (
    PeriodicBriefHtmlSink,
)


# ── Direct-call tests (no atexit) ────────────────────────────────────


def test_finalize_prints_brief_to_console(monkeypatch, tmp_path):
    """``finalize()`` should print a brief block to stdout.

    This is the path test code uses; the production path is atexit
    (see test_atexit_hook_prints_brief_at_interpreter_exit).
    """
    # Force a TTY-ish stdout so the color path runs at least once.
    # We don't assert on color codes themselves — the rendered words
    # are what matters.
    buf = StringIO()
    monkeypatch.setattr(sys, "stdout", buf)

    sink = PeriodicBriefHtmlSink(
        path=str(tmp_path / "brief.html"),
        print_to_console=True,
    )
    sink({"source": "bbc_world", "title": "test news", "url": "x"})
    sink({"type": "weather", "city": "Pasadena", "conditions": "Sunny"})
    sink.finalize()

    output = buf.getvalue()
    assert "WEATHER" in output, "Weather section heading missing from terminal output"
    assert "NEWS" in output, "News section heading missing from terminal output"
    assert "test news" in output, "News headline missing from terminal output"
    assert "Saved to:" in output, "Footer with path missing from terminal output"


def test_finalize_is_idempotent_for_console_print(monkeypatch, tmp_path):
    """Calling ``finalize()`` twice must not print the brief twice.

    The ``_printed`` guard prevents the atexit hook + an explicit
    finalize call (or two explicit finalize calls) from doubling up.
    """
    buf = StringIO()
    monkeypatch.setattr(sys, "stdout", buf)

    sink = PeriodicBriefHtmlSink(
        path=str(tmp_path / "brief.html"),
        print_to_console=True,
    )
    sink({"source": "bbc_world", "title": "only-once", "url": "x"})

    sink.finalize()
    first_call = buf.getvalue()
    sink.finalize()
    after_second_call = buf.getvalue()

    assert first_call == after_second_call, (
        "Second finalize() printed again — the _printed guard isn't working"
    )
    assert first_call.count("only-once") == 1


def test_print_to_console_false_suppresses_terminal_output(monkeypatch, tmp_path):
    """``print_to_console=False`` must not print anything to the terminal.

    Headless deployments (cron / systemd / CI) opt out via this flag
    and would not want surprise stdout writes at shutdown.
    """
    buf = StringIO()
    monkeypatch.setattr(sys, "stdout", buf)

    sink = PeriodicBriefHtmlSink(
        path=str(tmp_path / "brief.html"),
        print_to_console=False,
    )
    sink({"source": "bbc_world", "title": "silent", "url": "x"})
    sink.finalize()

    assert buf.getvalue() == "", (
        f"finalize() printed something despite print_to_console=False: "
        f"{buf.getvalue()!r}"
    )


# ── Atexit subprocess test ────────────────────────────────────────────


def test_atexit_hook_prints_brief_at_interpreter_exit(tmp_path):
    """The atexit hook must fire on natural interpreter exit.

    The framework only calls ``agent.shutdown()`` on the Sink BLOCK
    wrapping the instance, never on the instance itself. The brief is
    printed because we register an atexit hook at __init__ time, NOT
    because the framework calls finalize(). If a future refactor
    removes the atexit registration, this test fires.

    We run the scenario in a subprocess because atexit fires once per
    interpreter — testing it within pytest's own process is unreliable.
    """
    brief_path = tmp_path / "brief.html"
    script = dedent(
        f"""\
        import sys
        from dissyslab.gallery.apps.periodic_brief.sinks.periodic_brief_html_sink \\
            import PeriodicBriefHtmlSink

        sink = PeriodicBriefHtmlSink(
            path={str(brief_path)!r},
            print_to_console=True,
        )
        sink({{"source": "bbc_world", "title": "atexit fired me", "url": "x"}})

        # Print a sentinel BEFORE the interpreter exits so we can
        # distinguish "atexit ran after" from "atexit didn't run".
        print("---BEFORE-EXIT---", flush=True)

        # NO explicit finalize() call — we want the atexit hook to be
        # the ONLY thing that produces the brief output. If the brief
        # appears in stdout, the atexit wiring works.
        """
    )

    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        timeout=15,
    )

    assert result.returncode == 0, (
        f"Subprocess exited with code {result.returncode}\n"
        f"stderr: {result.stderr}"
    )

    output = result.stdout
    assert "---BEFORE-EXIT---" in output, "Sentinel missing — script didn't run cleanly"

    # The atexit print must appear AFTER the sentinel — meaning the
    # interpreter began shutting down and our hook ran during it.
    sentinel_idx = output.index("---BEFORE-EXIT---")
    after_sentinel = output[sentinel_idx:]
    assert "NEWS" in after_sentinel, (
        "Atexit hook didn't fire — no NEWS section in post-sentinel output.\n"
        f"Full subprocess stdout:\n{output}"
    )
    assert "atexit fired me" in after_sentinel, (
        "Atexit hook didn't include the news content we fed in"
    )


def test_atexit_hook_is_not_registered_when_print_to_console_false(tmp_path):
    """``print_to_console=False`` must skip the atexit registration entirely.

    A headless deployment that's instantiating dozens of sinks (one
    per office, perhaps) should not accumulate dozens of atexit
    callbacks. We assert by running a subprocess and verifying NO
    brief output appears at exit.
    """
    brief_path = tmp_path / "brief.html"
    script = dedent(
        f"""\
        from dissyslab.gallery.apps.periodic_brief.sinks.periodic_brief_html_sink \\
            import PeriodicBriefHtmlSink

        sink = PeriodicBriefHtmlSink(
            path={str(brief_path)!r},
            print_to_console=False,
        )
        sink({{"source": "bbc_world", "title": "should-not-print", "url": "x"}})
        print("---DONE---", flush=True)
        """
    )

    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        timeout=15,
    )

    assert result.returncode == 0
    assert "---DONE---" in result.stdout
    assert "should-not-print" not in result.stdout, (
        "Headless mode (print_to_console=False) leaked the news content "
        "to stdout at exit — the atexit hook should never have been "
        "registered."
    )
    assert "NEWS" not in result.stdout
