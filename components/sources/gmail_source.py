# components/sources/gmail_source.py
"""
Gmail Source — Poll Gmail inbox via IMAP and yield new emails.

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
    Sources: gmail(poll_interval=60, max_emails=10, unread_only=True)

Example Python:
    from components.sources.gmail_source import GmailSource
    from dsl.blocks import Source

    source = GmailSource(poll_interval=60, unread_only=True)
    node = Source(fn=source.run, name="gmail")
"""

import imaplib
import email
import os
import time
from email.header import decode_header
from typing import Optional


class GmailSource:
    """
    Poll Gmail inbox via IMAP and yield new emails as DisSysLab messages.

    Reads credentials from environment variables:
        GMAIL_USER         — your Gmail address
        GMAIL_APP_PASSWORD — app password from Google account settings

    Each email is yielded as a dict:
        {
            "source":    "gmail",
            "subject":   str,
            "sender":    str,
            "text":      str,   # plain text body
            "timestamp": str,   # date string from email headers
            "uid":       str,   # unique email ID
        }

    Args:
        poll_interval: Seconds between inbox checks (default: 60)
        max_emails:    Max emails to fetch per poll (default: 10)
        unread_only:   Only yield unread emails (default: True)
        folder:        Mailbox folder to monitor (default: "INBOX")
        user_env:      Environment variable for Gmail address (default: GMAIL_USER)
        password_env:  Environment variable for app password (default: GMAIL_APP_PASSWORD)
    """

    IMAP_SERVER = "imap.gmail.com"
    IMAP_PORT = 993

    def __init__(
        self,
        poll_interval: int = 60,
        max_emails: int = 10,
        unread_only: bool = True,
        folder: str = "INBOX",
        user_env: str = "GMAIL_USER",
        password_env: str = "GMAIL_APP_PASSWORD",
    ):
        self.poll_interval = poll_interval
        self.max_emails = max_emails
        self.unread_only = unread_only
        self.folder = folder

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

        self._seen_uids = set()

    def _connect(self):
        """Connect to Gmail IMAP server and return a logged-in connection."""
        mail = imaplib.IMAP4_SSL(self.IMAP_SERVER, self.IMAP_PORT)
        mail.login(self.user, self.password)
        return mail

    def _decode_header_value(self, value):
        """Decode email header value (handles encoded headers)."""
        if value is None:
            return ""
        decoded_parts = decode_header(value)
        parts = []
        for part, charset in decoded_parts:
            if isinstance(part, bytes):
                try:
                    parts.append(part.decode(
                        charset or "utf-8", errors="replace"))
                except Exception:
                    parts.append(part.decode("utf-8", errors="replace"))
            else:
                parts.append(str(part))
        return " ".join(parts).strip()

    def _get_body(self, msg):
        """Extract plain text body from email message."""
        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                disposition = str(part.get("Content-Disposition", ""))
                if content_type == "text/plain" and "attachment" not in disposition:
                    try:
                        charset = part.get_content_charset() or "utf-8"
                        body = part.get_payload(decode=True).decode(
                            charset, errors="replace")
                        break
                    except Exception:
                        continue
        else:
            try:
                charset = msg.get_content_charset() or "utf-8"
                body = msg.get_payload(decode=True).decode(
                    charset, errors="replace")
            except Exception:
                body = ""
        return body.strip()

    def _fetch_emails(self):
        """Connect to Gmail and fetch new emails. Returns list of dicts."""
        results = []
        try:
            mail = self._connect()
            mail.select(self.folder)

            # Search for unread or all emails
            search_criteria = "UNSEEN" if self.unread_only else "ALL"
            _, data = mail.search(None, search_criteria)

            uids = data[0].split()
            if not uids:
                mail.logout()
                return []

            # Take most recent max_emails
            uids = uids[-self.max_emails:]

            for uid in uids:
                uid_str = uid.decode()
                if uid_str in self._seen_uids:
                    continue

                _, msg_data = mail.fetch(uid, "(RFC822)")
                raw = msg_data[0][1]
                msg = email.message_from_bytes(raw)

                subject = self._decode_header_value(msg.get("Subject", ""))
                sender = self._decode_header_value(msg.get("From", ""))
                timestamp = self._decode_header_value(msg.get("Date", ""))
                body = self._get_body(msg)

                if not body:
                    body = subject

                self._seen_uids.add(uid_str)
                results.append({
                    "source":    "gmail",
                    "subject":   subject,
                    "sender":    sender,
                    "text":      body,
                    "timestamp": timestamp,
                    "uid":       uid_str,
                })

            mail.logout()

        except Exception as e:
            print(f"[GmailSource] Error: {e}")

        return results

    def run(self):
        """
        Generator that polls Gmail and yields new emails as DisSysLab messages.
        Runs forever, sleeping poll_interval seconds between checks.
        DisSysLab's Source block wraps this generator automatically.
        """
        print(f"[GmailSource] Monitoring {self.user} ({self.folder})")
        print(f"[GmailSource] Polling every {self.poll_interval}s")
        if self.unread_only:
            print(f"[GmailSource] Fetching unread emails only")

        while True:
            print(f"[GmailSource] Checking inbox...")
            emails = self._fetch_emails()
            print(f"[GmailSource] Found {len(emails)} new email(s)")
            for msg in emails:
                yield msg
            print(f"[GmailSource] Sleeping {self.poll_interval}s...")
            time.sleep(self.poll_interval)


# ── Convenience factory for office_utils SOURCE_REGISTRY ─────────────────────

def gmail(
    poll_interval: int = 60,
    max_emails: int = 10,
    unread_only: bool = True,
    folder: str = "INBOX",
) -> GmailSource:
    return GmailSource(
        poll_interval=poll_interval,
        max_emails=max_emails,
        unread_only=unread_only,
        folder=folder,
    )


# ── Test when run directly ────────────────────────────────────────────────────

if __name__ == "__main__":
    print("GmailSource — Test")
    print("=" * 60)
    print("Requires: GMAIL_USER and GMAIL_APP_PASSWORD env vars")
    print("-" * 60)

    source = GmailSource(poll_interval=30, max_emails=5, unread_only=True)

    count = 0
    for msg in source.run():
        count += 1
        print(f"\n{count}. From: {msg['sender']}")
        print(f"   Subject: {msg['subject']}")
        print(f"   Date: {msg['timestamp']}")
        print(f"   Preview: {msg['text'][:100]}")
        if count >= 3:
            print("\n[Stopping after 3 emails for test]")
            break
