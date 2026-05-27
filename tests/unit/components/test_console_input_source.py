"""Tests for ``ConsoleInputSource`` (registry name ``console_input``)."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from dissyslab.components.sources.console_input_source import ConsoleInputSource


def test_tty_reads_one_line() -> None:
    src = ConsoleInputSource()
    with patch("sys.stdin.isatty", return_value=True):
        with patch("builtins.input", return_value="hello"):
            assert src.run() == "hello"


def test_tty_eof_finishes() -> None:
    src = ConsoleInputSource()
    with patch("sys.stdin.isatty", return_value=True):
        with patch("builtins.input", side_effect=EOFError):
            assert src.run() is None
    assert src.run() is None


def test_headless_uses_default_message_once() -> None:
    src = ConsoleInputSource(default_message="seed line")
    with patch("sys.stdin.isatty", return_value=False):
        assert src.run() == "seed line"
        assert src.run() is None


def test_headless_prefers_default_over_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OFFICE_CONSOLE_INPUT", "from env")
    src = ConsoleInputSource(default_message="from default")
    with patch("sys.stdin.isatty", return_value=False):
        assert src.run() == "from default"


def test_headless_env_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OFFICE_CONSOLE_INPUT", "from env")
    src = ConsoleInputSource()
    with patch("sys.stdin.isatty", return_value=False):
        assert src.run() == "from env"
        assert src.run() is None


def test_headless_no_seed_returns_none() -> None:
    src = ConsoleInputSource()
    with patch("sys.stdin.isatty", return_value=False):
        assert src.run() is None
