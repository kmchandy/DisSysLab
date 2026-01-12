# components/sinks/mock_email_alerter.py

"""
MockEmailAlerter: Simulates email alerts by printing to console.

This is the mock version of GmailAlerter used in Module 2 (basic examples).
It has the exact same interface as GmailAlerter but prints to console instead
of sending real emails.

In Module 9, students replace this with the real GmailAlerter.
"""

from typing import Optional, Dict, Any
from datetime import datetime


class MockEmailAlerter:
    """
    Mock email alerter that prints alerts to console instead of sending emails.

    This mirrors the GmailAlerter interface exactly, making it easy to swap
    mock → real when students progress from Module 2 to Module 9.

    Example:
        >>> from components.sinks.mock_email_alerter import MockEmailAlerter
        >>> alerter = MockEmailAlerter(
        ...     to_address="admin@example.com",
        ...     subject_prefix="[ALERT]"
        ... )
        >>> alerter.run({"text": "Spam detected!"})
        # Prints formatted alert to console
    """

    def __init__(
        self,
        to_address: Optional[str] = None,
        from_address: Optional[str] = None,
        subject_prefix: str = "[ALERT]"
    ):
        """
        Initialize the mock email alerter.

        Args:
            to_address: Email address alerts would be sent to
            from_address: Email address alerts would be sent from
            subject_prefix: Prefix for email subject lines

        Note: These parameters match GmailAlerter for easy swapping.
              In mock mode, they're just used for display.
        """
        self.to_address = to_address or "admin@example.com"
        self.from_address = from_address or "noreply@example.com"
        self.subject_prefix = subject_prefix

        # Statistics
        self.alert_count = 0

    def run(self, msg: Dict[str, Any]):
        """
        Simulate sending an email alert by printing to console.

        This is the main method called by the DSL's sink_map decorator.
        It mirrors GmailAlerter.run() exactly.

        Args:
            msg: Dictionary containing message data
        """
        self.alert_count += 1

        # Extract content
        text = msg.get('text', str(msg))
        subject = msg.get('subject', 'Alert')

        # Print formatted alert
        print()
        print("=" * 70)
        print(f"📧 MOCK EMAIL ALERT #{self.alert_count}")
        print("=" * 70)
        print(f"From:    {self.from_address}")
        print(f"To:      {self.to_address}")
        print(f"Subject: {self.subject_prefix} {subject}")
        print()
        print("Message:")
        print(text)
        print()

        # Show additional fields if present
        other_fields = {k: v for k, v in msg.items() if k not in [
            'text', 'subject']}
        if other_fields:
            print("Additional Details:")
            for key, value in other_fields.items():
                print(f"  {key}: {value}")
            print()

        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 70)
        print()

    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics for this alerter.

        Returns:
            Dictionary with alert_count, etc.
        """
        return {
            "from_address": self.from_address,
            "to_address": self.to_address,
            "alerts_sent": self.alert_count,
            "mode": "mock"
        }

    def print_stats(self):
        """Print statistics in a readable format."""
        stats = self.get_stats()
        print()
        print("=" * 70)
        print("Mock Email Alerter Statistics")
        print("=" * 70)
        print(f"From:         {stats['from_address']}")
        print(f"To:           {stats['to_address']}")
        print(f"Alerts sent:  {stats['alerts_sent']} (printed to console)")
        print(f"Mode:         Mock (no real emails)")
        print("=" * 70)
        print()

    def finalize(self):
        """Cleanup - prints summary."""
        self.print_stats()


# ============================================================================
# Convenience Factory Functions (mirror GmailAlerter)
# ============================================================================

def create_spam_alerter(recipient: Optional[str] = None) -> MockEmailAlerter:
    """
    Create a mock email alerter configured for spam notifications.

    Args:
        recipient: Email address alerts would be sent to

    Returns:
        MockEmailAlerter configured for spam alerts
    """
    return MockEmailAlerter(
        to_address=recipient or "security@example.com",
        subject_prefix="[SPAM DETECTED]"
    )


def create_urgency_alerter(recipient: Optional[str] = None) -> MockEmailAlerter:
    """
    Create a mock email alerter configured for urgent notifications.

    Args:
        recipient: Email address alerts would be sent to

    Returns:
        MockEmailAlerter configured for urgent alerts
    """
    return MockEmailAlerter(
        to_address=recipient or "admin@example.com",
        subject_prefix="[URGENT]"
    )
