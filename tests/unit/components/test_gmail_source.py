"""The Gmail source reads mail without marking it read, and sends each email once."""

from __future__ import annotations

from email.message import EmailMessage

from dissyslab.components.sources import gmail_source


def _raw(subject: str, body: str) -> bytes:
    m = EmailMessage()
    m["Subject"], m["From"], m["Date"] = subject, "Sara <sara@example.edu>", "Wed, 29 Apr 2026 14:21:32 -0700"
    m["Message-ID"] = "<abc@example.edu>"
    m.set_content(body)
    return m.as_bytes()


class FakeIMAP:
    fetched: list[str] = []

    def __init__(self, *args):
        pass

    def login(self, user, password):
        pass

    def select(self, folder):
        pass

    def search(self, charset, criteria):
        return "OK", [b"1 2"]

    def fetch(self, uid, spec):
        FakeIMAP.fetched.append(spec)
        subject = {b"1": "PS3 office hours", b"2": "Deadline"}[uid]
        return "OK", [(b"header", _raw(subject, f"about {subject}"))]

    def logout(self):
        pass


def test_mail_is_read_with_peek_and_sent_once(monkeypatch):
    monkeypatch.setenv("GMAIL_USER", "you@gmail.com")
    monkeypatch.setenv("GMAIL_APP_PASSWORD", "xxxx")
    monkeypatch.setattr(gmail_source.imaplib, "IMAP4_SSL", FakeIMAP)
    FakeIMAP.fetched = []
    source = gmail_source.GmailSource()

    first = source._fetch_emails()
    assert [m["subject"] for m in first] == ["PS3 office hours", "Deadline"]
    assert first[0]["text"].strip() == "about PS3 office hours"
    assert first[0]["sender"] == "Sara <sara@example.edu>"
    assert set(first[0]) >= {"source", "title", "text", "url", "timestamp", "subject", "sender", "uid"}
    # BODY.PEEK[] does not set the Seen flag; RFC822 would mark the mail read.
    assert FakeIMAP.fetched == ["(BODY.PEEK[])", "(BODY.PEEK[])"]

    # The mail is still unread, so the next poll finds it again: the source
    # remembers what it has sent and sends nothing twice.
    assert source._fetch_emails() == []
