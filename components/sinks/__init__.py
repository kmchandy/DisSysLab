"""
Sinks: Processing nodes that receive and display or store messages.

Available sinks:
- ConsoleDisplay: Prints messages to console
- DemoEmailAlerter: Simulates email alerts by printing to console
- JSONLRecorder: Records messages to a JSON Line file
"""
from .console_display import ConsoleDisplay
from .demo_email_alerter import DemoEmailAlerter
from .sink_jsonl_recorder import JSONLRecorder

__all__ = ['ConsoleDisplay', 'DemoEmailAlerter', 'JSONLRecorder',]
