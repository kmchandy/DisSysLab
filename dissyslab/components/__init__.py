# dissyslab/components/__init__.py

"""
Components: the sources and sinks an office is built from.

- sources/: where messages come from (RSS feeds, files, sensors, APIs)
- sinks/: where they end (console, files, email, Slack)

Each is looked up by name through the registry in
``dissyslab/office/utils.py``.
"""

from . import sinks, sources

__all__ = ["sources", "sinks"]
