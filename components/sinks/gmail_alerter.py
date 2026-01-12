# components/sinks/gmail_alerter.py

"""
GmailAlerter: Send email alerts using Gmail SMTP

This component sends email notifications via Gmail's SMTP server.
It's designed to work as a sink in the DSL network.
"""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, Dict, Any
from datetime import datetime


class GmailAlerter:
    """
    Email alerter that sends messages via Gmail SMTP.

    This class sends email alerts and is designed to work as a sink
    in the DSL network using the sink_map decorator.

    Example:
        >>> alerter = GmailAlerter(
        ...     to_address="alerts@example.com",
        ...     subject_prefix="[ALERT]"
        ... )
        >>> alerter.run({"text": "Spam detected!"})
        # Sends email to alerts@example.com
    """

    def __init__(
        self,
        to_address: Optional[str] = None,
        from_address: Optional[str] = None,
        app_password: Optional[str] = None,
        subject_prefix: str = "[ALERT]",
        smtp_server: str = "smtp.gmail.com",
        smtp_port: int = 587,
        fallback_to_console: bool = True
    ):
        """
        Initialize the Gmail alerter.

        Args:
            to_address: Email address to send alerts to (default: from env or from_address)
            from_address: Gmail address to send from (default: GMAIL_ADDRESS env var)
            app_password: Gmail app password (default: GMAIL_APP_PASSWORD env var)
            subject_prefix: Prefix for email subject lines
            smtp_server: SMTP server address
            smtp_port: SMTP port (587 for TLS)
            fallback_to_console: If True, print to console if email fails

        Raises:
            ValueError: If credentials are not provided and not in environment
        """
        # Get credentials from parameters or environment
        self.from_address = from_address or os.environ.get("GMAIL_ADDRESS")
        self.app_password = app_password or os.environ.get(
            "GMAIL_APP_PASSWORD")

        if not self.from_address or not self.app_password:
            if fallback_to_console:
                print(
                    "[GmailAlerter] WARNING: Gmail credentials not found, using console fallback")
                print("Set GMAIL_ADDRESS and GMAIL_APP_PASSWORD to enable email")
                print("See setup/02_gmail_smtp_setup.md for instructions")
                self.fallback_mode = True
            else:
                raise ValueError(
                    "Gmail credentials not found. Either:\n"
                    "1. Set environment variables: GMAIL_ADDRESS and GMAIL_APP_PASSWORD\n"
                    "2. Pass parameters: GmailAlerter(from_address='...', app_password='...')\n"
                    "See setup/02_gmail_smtp_setup.md for detailed instructions."
                )
        else:
            self.fallback_mode = False

        # Set recipient (default to sender if not specified)
        self.to_address = to_address or self.from_address

        self.subject_prefix = subject_prefix
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.fallback_to_console = fallback_to_console

        # Statistics
        self.email_count = 0
        self.error_count = 0

    def run(self, msg: Dict[str, Any]):
        """
        Send an email alert.

        This is the main method called by the DSL's sink_map decorator.

        Args:
            msg: Dictionary containing message data
                Expected keys: 'text' (required), 'subject' (optional)
        """
        # Use fallback if credentials not available
        if self.fallback_mode:
            self._console_fallback(msg)
            return

        try:
            # Extract content
            text = msg.get('text', str(msg))
            subject = msg.get('subject', 'Alert')

            # Create email
            email_msg = MIMEMultipart()
            email_msg['From'] = self.from_address
            email_msg['To'] = self.to_address
            email_msg['Subject'] = f"{self.subject_prefix} {subject}"

            # Build email body
            body = self._format_email_body(msg)
            email_msg.attach(MIMEText(body, 'plain'))

            # Send email
            self._send_email(email_msg)

            self.email_count += 1
            print(f"[GmailAlerter] ✓ Email sent to {self.to_address}")

        except Exception as e:
            self.error_count += 1
            print(f"[GmailAlerter] ❌ Error sending email: {e}")

            if self.fallback_to_console:
                print("[GmailAlerter] Falling back to console output")
                self._console_fallback(msg)

    def _send_email(self, msg: MIMEMultipart):
        """Send email via SMTP."""
        server = smtplib.SMTP(self.smtp_server, self.smtp_port)
        server.starttls()
        server.login(self.from_address, self.app_password)
        server.send_message(msg)
        server.quit()

    def _format_email_body(self, msg: Dict[str, Any]) -> str:
        """
        Format message dictionary into email body.

        Args:
            msg: Message dictionary

        Returns:
            Formatted email body as string
        """
        lines = []
        lines.append("=" * 60)
        lines.append("ALERT NOTIFICATION")
        lines.append("=" * 60)
        lines.append(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")

        # Add main text
        if 'text' in msg:
            lines.append("Message:")
            lines.append(msg['text'])
            lines.append("")

        # Add other fields
        lines.append("Details:")
        for key, value in msg.items():
            if key != 'text':
                lines.append(f"  {key}: {value}")

        lines.append("=" * 60)
        lines.append("")
        lines.append("This is an automated alert from DisSysLab")

        return "\n".join(lines)

    def _console_fallback(self, msg: Dict[str, Any]):
        """Print to console as fallback when email fails."""
        print()
        print("=" * 60)
        print("📧 EMAIL ALERT (Console Fallback)")
        print("=" * 60)
        print(f"To: {self.to_address}")
        print(f"Subject: {self.subject_prefix} Alert")
        print()
        print(self._format_email_body(msg))
        print("=" * 60)
        print()

    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics for this alerter.

        Returns:
            Dictionary with email_count, error_count, etc.
        """
        return {
            "from_address": self.from_address,
            "to_address": self.to_address,
            "emails_sent": self.email_count,
            "errors": self.error_count,
            "fallback_mode": self.fallback_mode
        }

    def print_stats(self):
        """Print statistics in a readable format."""
        stats = self.get_stats()
        print("\n" + "=" * 60)
        print("Gmail Alerter Statistics")
        print("=" * 60)
        print(f"From:         {stats['from_address']}")
        print(f"To:           {stats['to_address']}")
        print(f"Emails sent:  {stats['emails_sent']}")
        print(f"Errors:       {stats['errors']}")
        if stats['fallback_mode']:
            print("Mode:         Console Fallback (credentials not configured)")
        else:
            print("Mode:         Gmail SMTP")
        print("=" * 60 + "\n")

    def finalize(self):
        """Cleanup - prints summary."""
        self.print_stats()


# ============================================================================
# Convenience Factory Function
# ============================================================================

def create_spam_alerter(recipient: Optional[str] = None) -> GmailAlerter:
    """
    Create a Gmail alerter configured for spam notifications.

    Args:
        recipient: Email address to send alerts to (default: sender's address)

    Returns:
        GmailAlerter configured for spam alerts
    """
    return GmailAlerter(
        to_address=recipient,
        subject_prefix="[SPAM DETECTED]",
        fallback_to_console=True
    )


def create_urgency_alerter(recipient: Optional[str] = None) -> GmailAlerter:
    """
    Create a Gmail alerter configured for urgent notifications.

    Args:
        recipient: Email address to send alerts to (default: sender's address)

    Returns:
        GmailAlerter configured for urgent alerts
    """
    return GmailAlerter(
        to_address=recipient,
        subject_prefix="[URGENT]",
        fallback_to_console=True
    )
