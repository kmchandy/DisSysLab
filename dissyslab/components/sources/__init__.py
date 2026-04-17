# components/sources/__init__.py

"""
Sources: Data stream origins for networks.

Available sources:
- DemoRSSSource: Demo RSS source with test data (no network needed)
- ListSource: Simple list-based source for testing
- RSSSource: Read real RSS/Atom feeds (requires network)
"""

from .demo_rss_source import DemoRSSSource
from .list_source import ListSource
from .rss_source import RSSSource

__all__ = ['DemoRSSSource', 'ListSource', 'RSSSource']
