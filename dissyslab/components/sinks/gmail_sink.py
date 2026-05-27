# dissyslab/components/sinks/gmail_sink.py
"""
Email Sink — Send emails via SMTP using a Gmail app password.

No OAuth needed. Uses Gmail app passwords — a simple string you
generate once in your Google account settings.

**Preview mode (no credentials):** if either ``GMAIL_USER`` or
``GMAIL_APP_PASSWORD`` is missing, ``gmail_sink`` does *not* raise.
Instead it appends each would-be email to ``outbox.md`` in the
current working directory so the user can see exactly what would
have been sent. Gallery apps ship with a placeholder recipient
like ``you@example.com``; first-time users get a working preview
out of the box, and switch to real sending by setting the two
environment variables.

Setup for real sending (one time):
    1. Go to myaccount.google.com → Security → 2-Step Verification (enable it)
    2. Go to myaccount.google.com → Security → App passwords
    3. Generate a new app password for "Mail"
    4. Set environment variables:
         export GMAIL_USER='you@gmail.com'
         export GMAIL_APP_PASSWORD='xxxx xxxx xxxx xxxx'

Example office.md:
    Sinks: gmail_sink(to="you@example.com", subject="DisSysLab Alert")

Example Python:
    from dissyslab.components.sinks.gmail_sink import GmailSink
    from dissyslab.blocks import Sink

    sink = GmailSink(to="you@example.com", subject="DisSysLab Alert")
    node = Sink(fn=sink.run, name="email_alert")
"""

import os
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path

from dissyslab.components.sinks.message_coerce import (
    coerce_sink_message,
    normalize_multibullet_lines,
)


class GmailSink:
    """
    Send each DisSysLab message as an email via SMTP — or preview it.

    Reads credentials from environment variables:
        GMAIL_USER         — your Gmail address
        GMAIL_APP_PASSWORD — app password from Google account settings

    When either env var is missing, the sink runs in **preview mode**:
    each message is appended to ``outbox.md`` in the working directory
    instead of being sent. This is the default for first-time users so
    the demo runs without any Gmail setup.

    The message's "text" field becomes the email body.
    The message's "subject" field overrides the default subject if present.

    Args:
        to:           Recipient email address
        subject:      Default subject line (overridden by message "subject" field)
        user_env:     Environment variable for Gmail address (default: GMAIL_USER)
        password_env: Environment variable for app password (default: GMAIL_APP_PASSWORD)
        outbox_path:  Where to write previews when credentials are missing
                      (default: ``outbox.md`` in current working directory)
    """

    SMTP_SERVER = "smtp.gmail.com"
    SMTP_PORT = 587

    def __init__(
        self,
        to: str,
        subject: str = "DisSysLab Alert",
        user_env: str = "GMAIL_USER",
        password_env: str = "GMAIL_APP_PASSWORD",
        outbox_path: str = "outbox.md",
    ):
        self.to = to
        self.subject = subject
        self.outbox_path = Path(outbox_path)

        self.user = os.environ.get(user_env)
        self.password = os.environ.get(password_env)

        self.preview_mode = not (self.user and self.password)
        self.emails_sent = 0
        self.previews_written = 0

        if self.preview_mode:
            # One announcement on startup so the user knows where the
            # preview file is. We do not raise — the office should still
            # run end-to-end.
            print(
                f"[gmail_sink] Preview mode — writing would-be emails to "
                f"{self.outbox_path.resolve()}\n"
                f"             (set {user_env} and {password_env} to send for real)"
            )

    # ── Internals ─────────────────────────────────────────────────────

    def _normalised_body(self, msg) -> tuple[str, str]:
        """Return (subject, body) ready for emailing or previewing."""
        subject = msg.get("subject", self.subject)
        body = msg.get("text", "") or str(msg)
        body = normalize_multibullet_lines(str(body))
        return subject, body

    def _write_preview(self, subject: str, body: str) -> None:
        """Append one would-be email to ``outbox.md`` as a Markdown block."""
        self.previews_written += 1
        stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        block = (
            f"\n---\n\n"
            f"## Email #{self.previews_written} — {stamp}\n\n"
            f"**To:** {self.to}  \n"
            f"**Subject:** {subject}\n\n"
            f"{body}\n"
        )
        # Append in text mode so the file stays human-readable.
        with self.outbox_path.open("a", encoding="utf-8") as fh:
            fh.write(block)
        print(
            f"[gmail_sink] preview #{self.previews_written} → "
            f"{self.outbox_path.name} (to={self.to}, subject={subject[:48]!r})"
        )

    def _send_real(self, subject: str, body: str) -> None:
        try:
            message = MIMEMultipart()
            message["From"] = self.user
            message["To"] = self.to
            message["Subject"] = subject
            message.attach(MIMEText(body, "plain"))

            with smtplib.SMTP(self.SMTP_SERVER, self.SMTP_PORT) as server:
                server.starttls()
                server.login(self.user, self.password)
                server.sendmail(self.user, self.to, message.as_string())

            self.emails_sent += 1
            print(
                f"[gmail_sink] sent #{self.emails_sent} to {self.to}: {subject[:50]}"
            )
        except Exception as e:
            print(f"[gmail_sink] error sending email: {e}")

    # ── DisSysLab sink interface ──────────────────────────────────────

    def run(self, msg):
        """
        Called by DisSysLab for each incoming message.

        In preview mode (no Gmail credentials), appends the message to
        ``outbox.md`` instead of sending. Otherwise sends a real email.

        Uses msg["subject"] as subject if present, otherwise uses the
        default subject passed at construction time. Uses msg["text"]
        as the email body.

        Args:
            msg: Dict message from upstream DisSysLab node
        """
        msg = coerce_sink_message(msg)
        subject, body = self._normalised_body(msg)

        if self.preview_mode:
            self._write_preview(subject, body)
        else:
            self._send_real(subject, body)


# ── Test when run directly ────────────────────────────────────────────────────

if __name__ == "__main__":
    print("GmailSink — Test")
    print("=" * 60)
    print("Requires: GMAIL_USER and GMAIL_APP_PASSWORD env vars")
    print("-" * 60)

    sink = GmailSink(
        to=os.environ.get("GMAIL_USER", "test@example.com"),
        subject="DisSysLab Test Email",
    )

    sink.run({
        "text": "This is a test message from DisSysLab GmailSink.",
        "source": "test",
    })

    print("✓ Test complete. Check your inbox.")
