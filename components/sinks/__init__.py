# components/sinks/__init__.py

"""
Sinks: Output destinations for network messages.

Available sinks:
- ConsoleSink: Print messages to console
- GmailAlerter: Send email alerts via Gmail SMTP (real)
- MockEmailAlerter: Mock email alerter for testing (Module 2)
"""

from .console_sink import ConsoleSink
from .gmail_alerter import GmailAlerter
from .mock_email_alerter import MockEmailAlerter

__all__ = ['ConsoleSink', 'GmailAlerter', 'MockEmailAlerter']
