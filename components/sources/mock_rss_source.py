# components/sources/mock_rss_source.py

"""
MockRSSSource: Simulates RSS feeds with test data.

This is the mock version of RSSSource used in Module 2 (basic examples).
It has the exact same interface as RSSSource but uses predefined test data
instead of fetching real feeds.

In Module 9, students replace this with the real RSSSource.
"""

from typing import Optional, Dict, Any


class MockRSSSource:
    """
    Mock RSS source that returns predefined articles.

    This mirrors the RSSSource interface exactly, making it easy to swap
    mock → real when students progress from Module 2 to Module 9.

    **Important:** Follows the Source pattern - run() returns values,
    not yields them. Returns None when exhausted.

    Example:
        >>> from components.sources import MockRSSSource
        >>> from dsl.blocks import Source
        >>> rss_data = MockRSSSource(feed_name="tech_news", max_articles=5)
        >>> rss_source = Source(fn=rss_data.run)
    """

    # Predefined test articles for different "feeds"
    MOCK_FEEDS = {
        "hacker_news": [
            "Show HN: Built a new Python library for distributed systems",
            "Ask HN: What are your favorite RSS feeds for tech news?",
            "Google announces new AI model with improved reasoning",
            "CLICK HERE for FREE cryptocurrency! Limited time only!",  # SPAM
            "Discussion: Best practices for building distributed networks",
            "Python 3.13 released with performance improvements",
            "ACT NOW! Make money fast with this one weird trick!",  # SPAM
            "Show HN: Open source alternative to commercial monitoring tool",
            "Breaking: Major security vulnerability discovered in popular library",
            "Tutorial: Building real-time data pipelines with Python"
        ],
        "tech_news": [
            "Startup raises $50M for AI-powered code analysis",
            "New framework promises to simplify microservices development",
            "BUY NOW! Get rich quick with automated trading!",  # SPAM
            "Interview: How we scaled to 1M concurrent users",
            "Study shows remote work increases developer productivity",
            "Limited time offer - click here for amazing deals!",  # SPAM
            "Open source project reaches 10k GitHub stars",
            "Company announces layoffs in tech sector restructuring",
            "Analysis: The future of edge computing",
            "Review: Best tools for monitoring distributed systems"
        ],
        "reddit_python": [
            "Just finished my first Django project! Feeling proud!",
            "What's the best way to handle async operations in Flask?",
            "FREE MONEY! Click this link now! Winner selected!",  # SPAM
            "TIL: Python's asyncio can significantly speed up I/O bound tasks",
            "My journey from bootcamp to senior developer",
            "Amazing discovery in Python internals",
            "You won't believe this one simple trick! Act now!",  # SPAM
            "Help: How do I optimize this database query?",
            "Show: Built a CLI tool for managing Docker containers",
            "Discussion: Is Python still relevant in 2025?"
        ]
    }

    def __init__(
        self,
        feed_name: str = "hacker_news",
        max_articles: Optional[int] = None,
        name: Optional[str] = None
    ):
        """
        Initialize the mock RSS source.

        Args:
            feed_name: Which mock feed to use ("hacker_news", "tech_news", "reddit_python")
            max_articles: Maximum number of articles to return (None = all)
            name: Name for this source (defaults to feed_name)
        """
        self.feed_name = feed_name
        self.max_articles = max_articles
        self.name = name or f"mock_{feed_name}"

        # Get the mock articles
        self.articles = self.MOCK_FEEDS.get(
            feed_name, self.MOCK_FEEDS["hacker_news"])

        # Limit if requested
        if max_articles:
            self.articles = self.articles[:max_articles]

        # State tracking (follows Source pattern)
        self.index = 0
        self._printed_header = False

    def run(self):
        """
        Returns next article or None when exhausted.

        This follows the Source pattern:
        - Returns a value (not yields)
        - Returns None when exhausted

        Returns:
            str: Next article text, or None if no more articles
        """
        # Print header on first call
        if not self._printed_header:
            print(
                f"[{self.name}] Fetching {len(self.articles)} articles from mock feed...")
            self._printed_header = True

        # Check if exhausted
        if self.index >= len(self.articles):
            return None

        # Get next article
        article = self.articles[self.index]
        self.index += 1

        return article

    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics for this source.

        Returns:
            Dictionary with fetched count, etc.
        """
        return {
            "name": self.name,
            "feed_name": self.feed_name,
            "total_articles": len(self.articles),
            "articles_fetched": self.index  # Use index directly
        }

    def print_stats(self):
        """Print statistics in a readable format."""
        stats = self.get_stats()
        print()
        print("=" * 60)
        print(f"Mock RSS Source Statistics: {stats['name']}")
        print("=" * 60)
        print(f"Feed:             {stats['feed_name']}")
        print(f"Total articles:   {stats['total_articles']}")
        print(f"Articles fetched: {stats['articles_fetched']}")
        print(f"Mode:             Mock (test data)")
        print("=" * 60)
        print()


# ============================================================================
# Convenience Factory Functions (mirror RSSSource)
# ============================================================================

def create_hacker_news_source(max_articles: int = 10) -> MockRSSSource:
    """
    Create a mock RSS source for Hacker News.

    Args:
        max_articles: Maximum number of articles to fetch

    Returns:
        MockRSSSource configured for Hacker News
    """
    return MockRSSSource(
        feed_name="hacker_news",
        max_articles=max_articles,
        name="mock_hacker_news"
    )


def create_tech_news_source(max_articles: int = 10) -> MockRSSSource:
    """
    Create a mock RSS source for technology news.

    Args:
        max_articles: Maximum articles to fetch

    Returns:
        MockRSSSource configured for tech news
    """
    return MockRSSSource(
        feed_name="tech_news",
        max_articles=max_articles,
        name="mock_tech_news"
    )


def create_reddit_source(subreddit: str = "python", max_articles: int = 10) -> MockRSSSource:
    """
    Create a mock RSS source for a Reddit subreddit.

    Args:
        subreddit: Name of the subreddit (currently only "python" supported in mock)
        max_articles: Maximum number of posts to fetch

    Returns:
        MockRSSSource configured for Reddit
    """
    return MockRSSSource(
        feed_name="reddit_python",
        max_articles=max_articles,
        name=f"mock_reddit_{subreddit}"
    )
