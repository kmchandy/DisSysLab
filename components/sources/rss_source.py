# components/rss_source.py

"""
RSSSource: Read and parse RSS/Atom feeds

This component reads RSS feeds and yields articles as messages.
No authentication required - perfect for teaching!
"""

import feedparser
from typing import List, Dict, Any, Optional
from datetime import datetime
import time


class RSSSource:
    """
    RSS feed reader that yields articles as messages.

    This class reads RSS/Atom feeds and yields structured data for each article.
    It's designed to work seamlessly with the DSL's source_map decorator.

    Example:
        >>> rss = RSSSource(urls=["https://hnrss.org/newest"])
        >>> for article in rss.run():
        ...     print(article['title'])
    """

    def __init__(
        self,
        urls: List[str],
        max_articles: Optional[int] = None,
        poll_interval: Optional[int] = None,
        name: str = "rss_source"
    ):
        """
        Initialize the RSS source.

        Args:
            urls: List of RSS/Atom feed URLs to read
            max_articles: Maximum number of articles to fetch (None = all)
            poll_interval: If set, poll feeds every N seconds (for persistent mode)
            name: Name for this source (for debugging)

        Examples of good RSS feeds:
            - Hacker News: "https://hnrss.org/newest"
            - NY Times Tech: "https://rss.nytimes.com/services/xml/rss/nyt/Technology.xml"
            - Reddit: "https://www.reddit.com/r/python/.rss"
            - BBC News: "http://feeds.bbci.co.uk/news/rss.xml"
        """
        self.urls = urls
        self.max_articles = max_articles
        self.poll_interval = poll_interval
        self.name = name

        # Track what we've seen (for persistent mode)
        self.seen_ids = set()

        # Statistics
        self.total_fetched = 0
        self.total_errors = 0

    def run(self):
        """
        Generator that yields articles from RSS feeds.

        Yields:
            str: Article text (title + description combined)

        For persistent mode (poll_interval set):
            Runs forever, polling feeds at regular intervals

        For one-shot mode (poll_interval None):
            Fetches feeds once and stops
        """
        if self.poll_interval:
            # Persistent mode: poll forever
            while True:
                yield from self._fetch_articles()
                print(f"[{self.name}] Sleeping for {self.poll_interval} seconds...")
                time.sleep(self.poll_interval)
        else:
            # One-shot mode: fetch once and stop
            yield from self._fetch_articles()

    def _fetch_articles(self):
        """Fetch articles from all configured feeds."""
        for url in self.urls:
            try:
                print(f"[{self.name}] Fetching {url}...")
                feed = feedparser.parse(url)

                if feed.bozo:
                    # Feed has parsing errors
                    print(f"[{self.name}] Warning: Feed parsing errors for {url}")

                # Get entries
                entries = feed.entries

                # Limit if requested
                if self.max_articles:
                    entries = entries[:self.max_articles]

                print(f"[{self.name}] Found {len(entries)} articles from {url}")

                for entry in entries:
                    # Create unique ID for deduplication
                    entry_id = entry.get('id', entry.get('link', ''))

                    # Skip if we've seen this before (in persistent mode)
                    if self.poll_interval and entry_id in self.seen_ids:
                        continue

                    # Mark as seen
                    self.seen_ids.add(entry_id)

                    # Extract article text
                    text = self._extract_text(entry)

                    if text:
                        self.total_fetched += 1
                        yield text

            except Exception as e:
                self.total_errors += 1
                print(f"[{self.name}] Error fetching {url}: {e}")

    def _extract_text(self, entry: Dict[str, Any]) -> str:
        """
        Extract text from a feed entry.

        Combines title and description/summary into a single text string.

        Args:
            entry: Feed entry dictionary from feedparser

        Returns:
            Combined text string
        """
        parts = []

        # Get title
        if 'title' in entry:
            parts.append(entry['title'])

        # Get description/summary
        if 'description' in entry:
            parts.append(entry['description'])
        elif 'summary' in entry:
            parts.append(entry['summary'])

        return " | ".join(parts)

    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics for this source.

        Returns:
            Dictionary with fetched count, error count, etc.
        """
        return {
            "name": self.name,
            "feeds": len(self.urls),
            "total_fetched": self.total_fetched,
            "total_errors": self.total_errors,
            "seen_ids": len(self.seen_ids)
        }

    def print_stats(self):
        """Print statistics in a readable format."""
        stats = self.get_stats()
        print("\n" + "=" * 60)
        print(f"RSS Source Statistics: {stats['name']}")
        print("=" * 60)
        print(f"Feeds configured: {stats['feeds']}")
        print(f"Articles fetched: {stats['total_fetched']}")
        print(f"Errors:           {stats['total_errors']}")
        print(f"Unique articles:  {stats['seen_ids']}")
        print("=" * 60 + "\n")


# ============================================================================
# Convenience Factory Functions
# ============================================================================

def create_hacker_news_source(max_articles: int = 10) -> RSSSource:
    """
    Create an RSS source for Hacker News.

    Args:
        max_articles: Maximum number of articles to fetch

    Returns:
        RSSSource configured for Hacker News
    """
    return RSSSource(
        urls=["https://hnrss.org/newest"],
        max_articles=max_articles,
        name="hacker_news"
    )


def create_tech_news_source(max_articles: int = 10) -> RSSSource:
    """
    Create an RSS source for technology news from multiple sources.

    Args:
        max_articles: Maximum articles per feed

    Returns:
        RSSSource configured for tech news
    """
    return RSSSource(
        urls=[
            "https://hnrss.org/newest",
            "https://rss.nytimes.com/services/xml/rss/nyt/Technology.xml",
        ],
        max_articles=max_articles,
        name="tech_news"
    )


def create_reddit_source(subreddit: str = "python", max_articles: int = 10) -> RSSSource:
    """
    Create an RSS source for a Reddit subreddit.

    Args:
        subreddit: Name of the subreddit (without r/)
        max_articles: Maximum number of posts to fetch

    Returns:
        RSSSource configured for Reddit
    """
    return RSSSource(
        urls=[f"https://www.reddit.com/r/{subreddit}/.rss"],
        max_articles=max_articles,
        name=f"reddit_{subreddit}"
    )
