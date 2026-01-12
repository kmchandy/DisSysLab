# components/sources/__init__.py

"""
Sources: Data stream origins for networks.

Available sources:
- RSSSource: Read RSS/Atom feeds (real, no auth needed)
- MockRSSSource: Mock RSS source for testing (Module 2)
- ListSource: Simple list-based source for testing
"""

from .rss_source import RSSSource
from .mock_rss_source import MockRSSSource
from .list_source import ListSource

__all__ = ['RSSSource', 'MockRSSSource', 'ListSource']
