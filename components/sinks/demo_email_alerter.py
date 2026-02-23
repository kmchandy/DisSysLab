# components/sinks/demo_email_alerter.py

"""
DemoEmailAlerter: Simulates email alerts by printing to console.

This is the demo version of GmailAlerter. It has the exact same interface
as GmailAlerter but prints to console instead of sending real emails.

When you're ready to send real emails, swap the import:
    from components.sinks.demo_email_alerter import DemoEmailAlerter  # demo
    from components.sinks.gmail_alerter import GmailAlerter           # real
"""

from typing import Optional, Dict, Any


class DemoEmailAlerter:
    """
    Simulates email alerts by printing formatted messages to the console.

    Mirrors the GmailAlerter interface exactly, making it a drop-in
    replacement when switching from demo to real email sending.

    Example:
        >>> alerter = DemoEmailAlerter(
        ...     to_address="admin@example.com",
        ...     subject_prefix="[ALERT]"
        ... )
        >>> alerter.run({"text": "Suspicious article detected!"})
    """

    def __init__(
        self,
        to_address: Optional[str] = None,
        from_address: Optional[str] = None,
        subject_prefix: str = "[ALERT]"
    ):
        """
        Initialize the demo email alerter.

        Args:
            to_address:     Email address alerts would be sent to
            from_address:   Email address alerts would be sent from
            subject_prefix: Prefix for email subject lines
        """
        self.to_address = to_address or "admin@example.com"
        self.from_address = from_address or "noreply@example.com"
        self.subject_prefix = subject_prefix
        self.alert_count = 0

    def __call__(self, msg: Dict[str, Any]):
        """
        Simulate sending an email alert by printing to the console.

        Args:
            msg: Dictionary containing message data
        """
        self.alert_count += 1
        print()
        print(f"  [ALERT - NEGATIVE]")
        print(f"  📧 To:      {self.to_address}")
        print(f"  📧 Subject: {self.subject_prefix} Negative article detected")
        icon = {"POSITIVE": "😊", "NEGATIVE": "😞", "NEUTRAL": "😐"}
        if isinstance(msg, dict) and "text" in msg:
            emoji = icon.get(msg.get("sentiment", ""), "📨")
            print(f"  {emoji} {msg['text']}")
        else:
            print(f"  📨 {msg}")
        print()

    run = __call__

    def get_stats(self) -> Dict[str, Any]:
        """Return usage statistics."""
        return {
            "from_address": self.from_address,
            "to_address":   self.to_address,
            "alert_count":  self.alert_count,
            "mode":         "demo"
        }


# ── Convenience factory functions ─────────────────────────────────────────────

def create_spam_alerter(recipient: Optional[str] = None) -> DemoEmailAlerter:
    """Create a DemoEmailAlerter configured for spam notifications."""
    return DemoEmailAlerter(
        to_address=recipient or "security@example.com",
        subject_prefix="[SPAM DETECTED]"
    )


def create_urgency_alerter(recipient: Optional[str] = None) -> DemoEmailAlerter:
    """Create a DemoEmailAlerter configured for urgent notifications."""
    return DemoEmailAlerter(
        to_address=recipient or "admin@example.com",
        subject_prefix="[URGENT]"
    )
