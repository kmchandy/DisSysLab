# components/sinks/gmail_sink.py
"""
Email Sink — Send emails via SMTP using Gmail app password.

No OAuth needed. Uses Gmail app passwords — a simple string you
generate once in your Google account settings.

Setup (one time):
    1. Go to myaccount.google.com → Security → 2-Step Verification (enable it)
    2. Go to myaccount.google.com → Security → App passwords
    3. Generate a new app password for "Mail"
    4. Set environment variables:
         export GMAIL_USER='you@gmail.com'
         export GMAIL_APP_PASSWORD='xxxx xxxx xxxx xxxx'

Example office.md:
    Sinks: gmail_sink(to="you@example.com", subject="DisSysLab Alert")

Example Python:
    from components.sinks.gmail_sink import GmailSink
    from dsl.blocks import Sink

    sink = GmailSink(to="you@example.com", subject="DisSysLab Alert")
    node = Sink(fn=sink.run, name="email_alert")
"""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


class GmailSink:
    """
    Send each DisSysLab message as an email via SMTP.

    Reads credentials from environment variables:
        GMAIL_USER         — your Gmail address
        GMAIL_APP_PASSWORD — app password from Google account settings

    The message's "text" field becomes the email body.
    The message's "subject" field overrides the default subject if present.

    Args:
        to:           Recipient email address
        subject:      Default subject line (overridden by message "subject" field)
        user_env:     Environment variable for Gmail address (default: GMAIL_USER)
        password_env: Environment variable for app password (default: GMAIL_APP_PASSWORD)
    """

    SMTP_SERVER = "smtp.gmail.com"
    SMTP_PORT = 587

    def __init__(
        self,
        to: str,
        subject: str = "DisSysLab Alert",
        user_env: str = "GMAIL_USER",
        password_env: str = "GMAIL_APP_PASSWORD",
    ):
        self.to = to
        self.subject = subject

        self.user = os.environ.get(user_env)
        self.password = os.environ.get(password_env)

        if not self.user or not self.password:
            raise ValueError(
                "Gmail credentials not found.\n"
                f"Set environment variables:\n"
                f"  export {user_env}='you@gmail.com'\n"
                f"  export {password_env}='your-app-password'\n"
                "Get an app password at: myaccount.google.com → Security → App passwords"
            )

        self.emails_sent = 0

    def run(self, msg):
        """
        Called by DisSysLab for each incoming message.
        Sends the message as an email.

        Uses msg["subject"] as subject if present, otherwise uses default.
        Uses msg["text"] as the email body.

        Args:
            msg: Dict message from upstream DisSysLab node
        """
        subject = msg.get("subject", self.subject)
        body = msg.get("text", str(msg))

        # Build a readable body if text is short or missing
        if not body:
            body = str(msg)

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
                f"[GmailSink] Sent email #{self.emails_sent} to {self.to}: {subject[:50]}")

        except Exception as e:
            print(f"[GmailSink] Error sending email: {e}")


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
