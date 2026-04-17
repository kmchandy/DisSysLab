# dissyslab/components/sources/rss_source.py

"""
RSSSource: Read and parse RSS/Atom feeds

This component reads RSS feeds and yields articles as messages.
No authentication required - perfect for teaching!

Usage:
    from dissyslab.components.sources.rss_source import RSSSource
    from dissyslab.blocks import Source

    rss = RSSSource(urls=["https://www.python.org/jobs/feed/rss/"], max_articles=5)
    source = Source(fn=rss.run, name="python_jobs")
    # No wrapper needed — Source handles generators automatically
"""

import re
import feedparser
from typing import List, Optional
import time


class RSSSource:
    """
    RSS feed reader that yields articles as messages.

    Yields one article per call to run(). Compatible with Source() directly —
    no generator wrapper needed in application code.

    Example:
        >>> rss = RSSSource(urls=["https://www.python.org/jobs/feed/rss/"])
        >>> source = Source(fn=rss.run, name="jobs")
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
            max_articles: Maximum number of articles to fetch per feed
                          (None = all)
            poll_interval: If set, poll feeds every N seconds
                           (for persistent/infinite mode)
            name: Name for this source (used in log messages)

        Example feeds:
            Python jobs:    "https://www.python.org/jobs/feed/rss/"
            Remote OK:      "https://remoteok.com/rss"
            Hacker News:    "https://hnrss.org/newest"
            NY Times Tech:  "https://rss.nytimes.com/services/xml/rss/nyt/Technology.xml"
            Reddit Python:  "https://www.reddit.com/r/python/.rss"
        """
        self.urls = urls
        self.max_articles = max_articles
        self.poll_interval = poll_interval
        self.name = name

        self.seen_ids = set()
        self.total_fetched = 0
        self.total_errors = 0

    def run(self):
        """
        Generator that yields one article (str) per iteration.

        Source() in dsl/blocks/source.py automatically wraps generators,
        so this works directly with Source(fn=rss.run, ...).

        In one-shot mode (poll_interval=None): fetches all feeds once.
        In polling mode (poll_interval set): runs forever.
        """
        if self.poll_interval:
            while True:
                yield from self._fetch_articles()
                print(f"[{self.name}] Sleeping {self.poll_interval}s...")
                time.sleep(self.poll_interval)
        else:
            yield from self._fetch_articles()

    def _fetch_articles(self):
        """Fetch and yield articles from all configured feed URLs."""
        for url in self.urls:
            try:
                print(f"[{self.name}] Fetching {url}...")
                feed = feedparser.parse(url)

                if feed.bozo:
                    print(f"[{self.name}] Warning: Feed parsing errors for {url}")

                entries = feed.entries
                if self.max_articles:
                    entries = entries[:self.max_articles]

                print(f"[{self.name}] Found {len(entries)} articles from {url}")

                for entry in entries:
                    entry_id = entry.get('id', entry.get('link', ''))

                    if self.poll_interval and entry_id in self.seen_ids:
                        continue
                    self.seen_ids.add(entry_id)

                    text = self._extract_text(entry)
                    if text:
                        self.total_fetched += 1
                        yield text

            except Exception as e:
                self.total_errors += 1
                print(f"[{self.name}] Error fetching {url}: {e}")

    def _extract_text(self, entry) -> str:
        """
        Extract plain text from a feed entry.

        Combines title and description/summary, then strips HTML tags
        so the result is clean plain text suitable for AI analysis.
        """
        parts = []

        if 'title' in entry:
            parts.append(entry['title'])

        if 'description' in entry:
            parts.append(entry['description'])
        elif 'summary' in entry:
            parts.append(entry['summary'])

        text = " | ".join(parts)

        # Strip HTML tags — RSS descriptions often contain raw HTML
        text = re.sub(r'<[^>]+>', ' ', text)

        # Decode common HTML entities
        text = text.replace('&amp;', '&')
        text = text.replace('&lt;', '<')
        text = text.replace('&gt;', '>')
        text = text.replace('&nbsp;', ' ')
        text = text.replace('&#39;', "'")
        text = text.replace('&quot;', '"')

        # Collapse whitespace
        text = re.sub(r'\s+', ' ', text).strip()

        return text

    def get_stats(self):
        return {
            "name":          self.name,
            "feeds":         len(self.urls),
            "total_fetched": self.total_fetched,
            "total_errors":  self.total_errors,
            "seen_ids":      len(self.seen_ids),
        }


# ── Convenience factory functions ─────────────────────────────────────────────

def create_hacker_news_source(max_articles: int = 10) -> RSSSource:
    return RSSSource(
        urls=["https://hnrss.org/newest"],
        max_articles=max_articles,
        name="hacker_news"
    )


def create_python_jobs_source(max_articles: int = 10) -> RSSSource:
    return RSSSource(
        urls=["https://www.python.org/jobs/feed/rss/"],
        max_articles=max_articles,
        name="python_jobs"
    )


def create_remote_jobs_source(max_articles: int = 10) -> RSSSource:
    return RSSSource(
        urls=["https://remoteok.com/rss"],
        max_articles=max_articles,
        name="remote_jobs"
    )


def create_reddit_source(subreddit: str = "python", max_articles: int = 10) -> RSSSource:
    return RSSSource(
        urls=[f"https://www.reddit.com/r/{subreddit}/.rss"],
        max_articles=max_articles,
        name=f"reddit_{subreddit}"
    )
