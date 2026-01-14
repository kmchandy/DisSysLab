"""
Sinks: Processing nodes that receive and display or store messages.

Available sinks:
- ConsoleDisplay: Prints messages to console
- MockEmailAlerter: Simulates email alerts by printing to console
- JSONLRecorder: Records messages to a JSON Line file
"""
from .console_display import ConsoleDisplay
from .mock_email_alerter import MockEmailAlerter
from .sink_jsonl_recorder import JSONLRecorder

__all__ = ['ConsoleDisplay', 'MockEmailAlerter', 'JSONLRecorder',]
