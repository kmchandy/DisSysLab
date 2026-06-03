# tests/unit/test_gmail_sink.py

"""
Unit tests for ``dissyslab.components.sinks.gmail_sink``.

Cover the recipient-placeholder substitution introduced with the
gallery-move pass: gallery offices ship with ``to="you@example.com"``
(RFC 2606 reserved domain). When the user has ``GMAIL_USER`` set,
that address is substituted for the placeholder so the user gets a
single-knob setup. Explicit non-placeholder addresses are passed
through untouched.

Also covers the older preview-mode behaviour for regression: with no
credentials, the sink writes to ``outbox.md`` instead of raising.

Tests run without ever touching the real SMTP path — credentials,
even when "set", are dummy strings that never reach a network call.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dissyslab.components.sinks.gmail_sink import GmailSink


# ── Recipient placeholder substitution ────────────────────────────────


def test_at_example_com_substitutes_gmail_user(monkeypatch, tmp_path):
    """The shipped placeholder ``to="you@example.com"`` is replaced
    with the user's GMAIL_USER address at construction time."""
    monkeypatch.setenv("GMAIL_USER", "pat@gmail.com")
    monkeypatch.setenv("GMAIL_APP_PASSWORD", "dummy")
    sink = GmailSink(
        to="you@example.com",
        outbox_path=str(tmp_path / "outbox.md"),
    )
    assert sink.to == "pat@gmail.com"


def test_substitution_is_case_insensitive(monkeypatch, tmp_path):
    """Office writers might capitalise the placeholder differently;
    the substitution should still fire."""
    monkeypatch.setenv("GMAIL_USER", "pat@gmail.com")
    monkeypatch.setenv("GMAIL_APP_PASSWORD", "dummy")
    sink = GmailSink(
        to="You@Example.COM",
        outbox_path=str(tmp_path / "outbox.md"),
    )
    assert sink.to == "pat@gmail.com"


def test_explicit_non_example_address_passes_through(monkeypatch, tmp_path):
    """An office that explicitly addresses a real recipient
    (e.g. ``to="boss@company.com"``) must NOT be substituted, even
    when GMAIL_USER is set."""
    monkeypatch.setenv("GMAIL_USER", "pat@gmail.com")
    monkeypatch.setenv("GMAIL_APP_PASSWORD", "dummy")
    sink = GmailSink(
        to="boss@company.com",
        outbox_path=str(tmp_path / "outbox.md"),
    )
    assert sink.to == "boss@company.com"


def test_no_substitution_when_gmail_user_unset(monkeypatch, tmp_path):
    """With no GMAIL_USER set, the placeholder remains literally in
    the ``to`` field. The user will see ``you@example.com`` in the
    outbox file — honest about being a placeholder."""
    monkeypatch.delenv("GMAIL_USER", raising=False)
    monkeypatch.delenv("GMAIL_APP_PASSWORD", raising=False)
    sink = GmailSink(
        to="you@example.com",
        outbox_path=str(tmp_path / "outbox.md"),
    )
    assert sink.to == "you@example.com"
    # And the sink is in preview mode (no creds).
    assert sink.preview_mode is True


def test_other_example_subdomains_not_substituted(monkeypatch, tmp_path):
    """Only ``@example.com`` triggers the substitution today. Other
    reserved domains (``example.org``, ``example.net``) and arbitrary
    sub-domains do not. Conservative scope keeps the rule predictable."""
    monkeypatch.setenv("GMAIL_USER", "pat@gmail.com")
    monkeypatch.setenv("GMAIL_APP_PASSWORD", "dummy")
    sink = GmailSink(
        to="you@example.org",
        outbox_path=str(tmp_path / "outbox.md"),
    )
    assert sink.to == "you@example.org"


# ── Preview mode (regression) ─────────────────────────────────────────


def test_preview_mode_writes_to_outbox(monkeypatch, tmp_path, capsys):
    """With no credentials, the sink runs in preview mode: instead
    of raising or attempting SMTP, it appends a markdown block to
    ``outbox.md`` in the working directory."""
    monkeypatch.delenv("GMAIL_USER", raising=False)
    monkeypatch.delenv("GMAIL_APP_PASSWORD", raising=False)
    outbox = tmp_path / "outbox.md"
    sink = GmailSink(to="you@example.com", outbox_path=str(outbox))
    sink.run({
        "subject": "Test subject",
        "text": "Hello, world.",
    })
    contents = outbox.read_text(encoding="utf-8")
    assert "Test subject" in contents
    assert "Hello, world." in contents
    assert "you@example.com" in contents  # placeholder shown honestly
