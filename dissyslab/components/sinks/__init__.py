"""
Sinks: Processing nodes that receive and display or store messages.

Available sinks:
- ConsoleDisplay: Prints messages to console
- JSONLRecorder: Records messages to a JSON Lines file

This file re-exports a small convenience subset. The full catalog
of shipped sinks is in dissyslab/office/utils.py SINK_REGISTRY and
documented in docs/SOURCES_AND_SINKS.md.
"""
from .console_display import ConsoleDisplay
from .sink_jsonl_recorder import JSONLRecorder

__all__ = ['ConsoleDisplay', 'JSONLRecorder']
