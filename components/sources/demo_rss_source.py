# components/sources/demo_rss_source.py

"""
DemoRSSSource: Simulates RSS feeds with test data.

This is the demo version of RSSSource — no network access needed.
It has the exact same .run() interface as RSSSource, so swapping
from demo to real is just changing the import and constructor.

Demo version:
    from components.sources.demo_rss_source import DemoRSSSource
    rss = DemoRSSSource(feed_name="hacker_news")

Real version:
    from components.sources.rss_source import RSSSource
    rss = RSSSource("https://news.ycombinator.com/rss")

Both work the same way: call rss.run() to get the next article.
"""

from typing import Optional, Dict, Any

# ── Predefined test articles ─────────────────────────────────────────

DEMO_FEEDS = {
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
        "Review: Best tools for monitoring distributed systems",
        "Critical security flaw patched in major web framework"
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
        "Discussion: Is Python still relevant in 2025?",
        "Emergency! Security breach in popular package."
    ]
}

DEMO_SOCIAL_FEEDS = {
    "example_posts_from_X": [
        "Just got promoted at work! Best day ever! 🎉",
        "Breaking: New tech announced!",
        "CLICK HERE for FREE MONEY! Limited time offer!",  # SPAM
        "Just had the best lunch ever",
        "ACT NOW! Buy now and save! Winner selected!"  # SPAM
    ],
    "example_posts_from_Reddit": [
        "Had an amazing coffee this morning ☕",
        "Amazing discovery in science",
        "Click here to claim your free money now!",  # SPAM
        "Looking forward to the weekend",
        "Excited to start my new project tomorrow!",
        "Limited time winner! Act now or miss out!"  # SPAM
    ],
    "example_posts_from_Facebook": [
        "Traffic is terrible today, stuck for 2 hours 😤",
        "Family vacation was incredible",
        "My package got lost in delivery again...",
        "Terrible customer service today"
    ]
}


class DemoRSSSource:
    """
    Demo RSS source that returns predefined articles.

    This mirrors the RSSSource interface exactly, making it easy to swap
    demo → real when you're ready to use live data.

    Each call to .run() returns the next article as a string.
    Returns None when all articles have been returned.

    Available feeds: "hacker_news", "tech_news", "reddit_python"

    Example:
        >>> from components.sources.demo_rss_source import DemoRSSSource
        >>> from dsl.blocks import Source
        >>> rss = DemoRSSSource(feed_name="hacker_news", max_articles=5)
        >>> source = Source(fn=rss.run, name="news")
    """

    def __init__(
        self,
        feed_name: str,
        max_articles: Optional[int] = None,
        name: Optional[str] = None
    ):
        """
        Create a demo RSS source.

        Args:
            feed_name: Which feed to use ("hacker_news", "tech_news", "reddit_python")
            max_articles: Maximum number of articles to return (None = all)
            name: Name for this source (defaults to feed_name)
        """
        self.feed_name = feed_name
        self.max_articles = max_articles
        self.name = name or feed_name

        # Get the articles for this feed
        self.articles = DEMO_FEEDS.get(feed_name, [])

        # Limit if requested
        if max_articles:
            self.articles = self.articles[:max_articles]

        # Track position
        self.index = 0

    def run(self):
        """
        Return the next article, or None when exhausted.

        Returns:
            str: Next article text, or None if no more articles.
        """
        if self.index >= len(self.articles):
            return None

        article = self.articles[self.index]
        self.index += 1
        return article

    # Allow calling the instance directly: source() is the same as source.run()
    __call__ = run

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics for this source."""
        return {
            "name": self.name,
            "feed_name": self.feed_name,
            "total_articles": len(self.articles),
            "articles_returned": self.index
        }

    def print_stats(self):
        """Print statistics in a readable format."""
        stats = self.get_stats()
        print()
        print("=" * 60)
        print(f"Demo RSS Source: {stats['name']}")
        print("=" * 60)
        print(f"  Feed:              {stats['feed_name']}")
        print(f"  Total articles:    {stats['total_articles']}")
        print(f"  Articles returned: {stats['articles_returned']}")
        print("=" * 60)
        print()


# ── Self-test ────────────────────────────────────────────────────────

if __name__ == "__main__":
    passed = 0
    failed = 0

    # Test 1: Basic iteration
    print("Test 1: Basic iteration (hacker_news, all articles)")
    rss = DemoRSSSource(feed_name="hacker_news")
    articles = []
    while True:
        article = rss.run()
        if article is None:
            break
        articles.append(article)
    expected = len(DEMO_FEEDS["hacker_news"])
    if len(articles) == expected:
        print(f"  ✓ Got {len(articles)} articles (expected {expected})")
        passed += 1
    else:
        print(f"  ✗ Got {len(articles)} articles (expected {expected})")
        failed += 1

    # Test 2: max_articles limits output
    print("Test 2: max_articles=3")
    rss = DemoRSSSource(feed_name="hacker_news", max_articles=3)
    articles = []
    while True:
        article = rss.run()
        if article is None:
            break
        articles.append(article)
    if len(articles) == 3:
        print(f"  ✓ Got 3 articles")
        passed += 1
    else:
        print(f"  ✗ Got {len(articles)} articles (expected 3)")
        failed += 1

    # Test 3: Returns None after exhaustion (multiple calls)
    print("Test 3: Returns None after exhaustion")
    rss = DemoRSSSource(feed_name="tech_news", max_articles=2)
    rss.run()  # article 1
    rss.run()  # article 2
    result1 = rss.run()  # should be None
    result2 = rss.run()  # should still be None
    if result1 is None and result2 is None:
        print(f"  ✓ Returns None after exhaustion")
        passed += 1
    else:
        print(f"  ✗ Expected None, got {result1}, {result2}")
        failed += 1

    # Test 4: Each article is a string
    print("Test 4: Articles are strings")
    rss = DemoRSSSource(feed_name="reddit_python", max_articles=3)
    all_strings = True
    for _ in range(3):
        article = rss.run()
        if not isinstance(article, str):
            all_strings = False
            break
    if all_strings:
        print(f"  ✓ All articles are strings")
        passed += 1
    else:
        print(f"  ✗ Not all articles are strings")
        failed += 1

    # Test 5: Different feeds return different data
    print("Test 5: Different feeds return different data")
    rss_hn = DemoRSSSource(feed_name="hacker_news", max_articles=1)
    rss_tech = DemoRSSSource(feed_name="tech_news", max_articles=1)
    article_hn = rss_hn.run()
    article_tech = rss_tech.run()
    if article_hn != article_tech:
        print(f"  ✓ Different feeds return different articles")
        passed += 1
    else:
        print(f"  ✗ Same article from different feeds")
        failed += 1

    # Test 6: get_stats tracks correctly
    print("Test 6: get_stats")
    rss = DemoRSSSource(feed_name="hacker_news", max_articles=5)
    rss.run()
    rss.run()
    rss.run()
    stats = rss.get_stats()
    if stats["articles_returned"] == 3 and stats["total_articles"] == 5:
        print(f"  ✓ Stats correct: 3 returned out of 5")
        passed += 1
    else:
        print(f"  ✗ Stats wrong: {stats}")
        failed += 1

    # Test 7: Unknown feed returns empty
    print("Test 7: Unknown feed name")
    rss = DemoRSSSource(feed_name="nonexistent_feed")
    result = rss.run()
    if result is None:
        print(f"  ✓ Unknown feed returns None immediately")
        passed += 1
    else:
        print(f"  ✗ Expected None, got {result}")
        failed += 1

    # Summary
    print()
    total = passed + failed
    print(f"Results: {passed}/{total} tests passed")
    if failed == 0:
        print("✓ All tests passed!")
    else:
        print(f"✗ {failed} test(s) failed")
