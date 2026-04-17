# dissyslab/components/sources/rss_normalizer.py

"""
RSSNormalizer: Converts RSSSource string output to the standard article dict.

Every article in a DisSysLab gallery pipeline has exactly these five keys:

    {
        "source":    str,   # feed URL or name — where the article came from
        "title":     str,   # headline
        "text":      str,   # full plain-text content (HTML stripped)
        "url":       str,   # link to original article
        "timestamp": str,   # publication date as ISO string, or "" if unavailable
    }

RSSNormalizer sits immediately after RSSSource in every gallery pipeline:

    RSSSource → RSSNormalizer → transforms → sinks

Usage:
    from dissyslab.components.sources.rss_source import RSSSource
    from dissyslab.components.sources.rss_normalizer import RSSNormalizer
    from dissyslab.blocks import Source, Transform

    rss        = RSSSource(urls=["https://hnrss.org/newest"], max_articles=20)
    normalizer = RSSNormalizer(source_name="hacker_news")

    source     = Source(fn=rss.run,          name="feed")
    normalize  = Transform(fn=normalizer.run, name="normalize")

Note:
    RSSSource.run() currently yields plain strings (title + description
    concatenated). RSSNormalizer re-parses the original feed entries to
    recover the individual fields. To do this it needs access to the same
    RSSSource instance so it can read the already-fetched entries.

    Simpler design: pass the RSSSource instance to RSSNormalizer and let
    it iterate entries directly, bypassing the string concatenation entirely.
"""

import re
from datetime import datetime, timezone
from typing import Optional
import feedparser


class RSSNormalizer:
    """
    Produces standard five-key article dicts from RSS feed entries.

    Rather than wrapping the string output of RSSSource (which has already
    lost the individual fields), RSSNormalizer fetches and iterates feed
    entries directly. It replaces RSSSource as the data-producing component
    when used in gallery pipelines.

    Args:
        urls:         List of RSS feed URLs (same as RSSSource)
        source_name:  Human-readable name for the source (e.g. "hacker_news")
        max_articles: Max articles per feed (None = all)
        poll_interval: If set, re-fetch feeds every N seconds

    Example:
        >>> normalizer = RSSNormalizer(
        ...     urls=["https://hnrss.org/newest"],
        ...     source_name="hacker_news",
        ...     max_articles=20
        ... )
        >>> source = Source(fn=normalizer.run, name="feed")
    """

    def __init__(
        self,
        urls: list,
        source_name: str = "rss",
        max_articles: Optional[int] = None,
        poll_interval: Optional[int] = None,
    ):
        self.urls = urls
        self.source_name = source_name
        self.max_articles = max_articles
        self.poll_interval = poll_interval

        self._seen_urls = set()
        self._count = 0

    def run(self):
        """
        Generator that yields one standard dict per article.

        Compatible with Source(fn=normalizer.run, name="...") directly —
        Source() in dsl/blocks/source.py auto-wraps generators.
        """
        import time
        if self.poll_interval:
            while True:
                yield from self._fetch()
                print(f"[{self.source_name}] Sleeping {self.poll_interval}s...")
                time.sleep(self.poll_interval)
        else:
            yield from self._fetch()

    def _fetch(self):
        """Fetch all configured feeds and yield standard dicts."""
        for url in self.urls:
            try:
                print(f"[{self.source_name}] Fetching {url}...")
                feed = feedparser.parse(url)
                entries = feed.entries

                if self.max_articles:
                    entries = entries[:self.max_articles]

                print(f"[{self.source_name}] {len(entries)} entries from {url}")

                for entry in entries:
                    article = self._to_standard_dict(entry, url)
                    if article is None:
                        continue

                    # De-duplicate by URL
                    if article["url"] in self._seen_urls:
                        continue
                    self._seen_urls.add(article["url"])

                    self._count += 1
                    yield article

            except Exception as e:
                print(f"[{self.source_name}] Error fetching {url}: {e}")

    def _to_standard_dict(self, entry, feed_url: str) -> Optional[dict]:
        """
        Convert a feedparser entry to the standard five-key dict.

        Returns None if the entry has no usable text.
        """
        # ── title ────────────────────────────────────────────────────────
        title = entry.get("title", "").strip()

        # ── text (description/summary, HTML stripped) ─────────────────────
        raw_text = (
            entry.get("description", "") or
            entry.get("summary",     "")
        ).strip()
        text = self._strip_html(raw_text)

        # If both title and text are empty, skip this entry
        if not title and not text:
            return None

        # Use title as text fallback and vice-versa
        if not text:
            text = title
        if not title:
            title = text[:80]

        # Hard guarantee: text must be non-empty after all fallbacks
        if not text.strip():
            return None

        # ── url ───────────────────────────────────────────────────────────
        url = entry.get("link", feed_url).strip()

        # ── timestamp ─────────────────────────────────────────────────────
        timestamp = self._parse_timestamp(entry)

        # ── source ────────────────────────────────────────────────────────
        source = self.source_name

        return {
            "source":    source,
            "title":     title,
            "text":      text,
            "url":       url,
            "timestamp": timestamp,
        }

    # ── helpers ───────────────────────────────────────────────────────────

    @staticmethod
    def _strip_html(text: str) -> str:
        """Remove HTML tags and decode common entities."""
        text = re.sub(r'<[^>]+>', ' ', text)
        text = text.replace('&amp;',  '&')
        text = text.replace('&lt;',   '<')
        text = text.replace('&gt;',   '>')
        text = text.replace('&nbsp;', ' ')
        text = text.replace('&#39;',  "'")
        text = text.replace('&quot;', '"')
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    @staticmethod
    def _parse_timestamp(entry) -> str:
        """Return ISO timestamp string, or empty string if unavailable."""
        for field in ("published", "updated", "created"):
            value = entry.get(field, "")
            if value:
                return str(value)
        # feedparser also provides parsed time tuples
        for field in ("published_parsed", "updated_parsed"):
            parsed = entry.get(field)
            if parsed:
                try:
                    dt = datetime(*parsed[:6], tzinfo=timezone.utc)
                    return dt.isoformat()
                except Exception:
                    pass
        return ""


# ── Convenience factory functions ─────────────────────────────────────────────

def hacker_news(max_articles: int = 20, poll_interval: Optional[int] = None) -> RSSNormalizer:
    return RSSNormalizer(
        urls=["https://hnrss.org/newest"],
        source_name="hacker_news",
        max_articles=max_articles,
        poll_interval=poll_interval,
    )


def mit_tech_review(max_articles: int = 10, poll_interval: Optional[int] = None) -> RSSNormalizer:
    return RSSNormalizer(
        urls=["https://www.technologyreview.com/feed/"],
        source_name="mit_tech_review",
        max_articles=max_articles,
        poll_interval=poll_interval,
    )


def techcrunch(max_articles: int = 10, poll_interval: Optional[int] = None) -> RSSNormalizer:
    return RSSNormalizer(
        urls=["https://techcrunch.com/feed/"],
        source_name="techcrunch",
        max_articles=max_articles,
        poll_interval=poll_interval,
    )


def venturebeat_ai(max_articles: int = 10, poll_interval: Optional[int] = None) -> RSSNormalizer:
    return RSSNormalizer(
        urls=["https://venturebeat.com/category/ai/feed/"],
        source_name="venturebeat_ai",
        max_articles=max_articles,
        poll_interval=poll_interval,
    )


def al_jazeera(max_articles: int = 20, poll_interval: Optional[int] = None) -> RSSNormalizer:
    return RSSNormalizer(
        urls=["https://www.aljazeera.com/xml/rss/all.xml"],
        source_name="al_jazeera",
        max_articles=max_articles,
        poll_interval=poll_interval,
    )


def npr_news(max_articles: int = 10, poll_interval: Optional[int] = None) -> RSSNormalizer:
    return RSSNormalizer(
        urls=["https://feeds.npr.org/1001/rss.xml"],
        source_name="npr_news",
        max_articles=max_articles,
        poll_interval=poll_interval,
    )


def bbc_world(max_articles: int = 20, poll_interval: Optional[int] = None) -> RSSNormalizer:
    return RSSNormalizer(
        urls=["https://feeds.bbci.co.uk/news/world/rss.xml"],
        source_name="bbc_world",
        max_articles=max_articles,
        poll_interval=poll_interval,
    )


def bbc_tech(max_articles: int = 20, poll_interval: Optional[int] = None) -> RSSNormalizer:
    return RSSNormalizer(
        urls=["https://feeds.bbci.co.uk/news/technology/rss.xml"],
        source_name="bbc_tech",
        max_articles=max_articles,
        poll_interval=poll_interval,
    )


def nasa_news(max_articles: int = 10, poll_interval: Optional[int] = None) -> RSSNormalizer:
    return RSSNormalizer(
        urls=["https://www.nasa.gov/rss/dyn/breaking_news.rss"],
        source_name="nasa",
        max_articles=max_articles,
        poll_interval=poll_interval,
    )


def python_jobs(max_articles: int = 20, poll_interval: Optional[int] = None) -> RSSNormalizer:
    return RSSNormalizer(
        urls=["https://www.python.org/jobs/feed/rss/"],
        source_name="python_jobs",
        max_articles=max_articles,
        poll_interval=poll_interval,
    )


def remoteok(max_articles: int = 20, poll_interval: Optional[int] = None) -> RSSNormalizer:
    return RSSNormalizer(
        urls=["https://remoteok.com/rss"],
        source_name="remoteok",
        max_articles=max_articles,
        poll_interval=poll_interval,
    )


def we_work_remotely(max_articles: int = 20, poll_interval: Optional[int] = None) -> RSSNormalizer:
    return RSSNormalizer(
        urls=["https://weworkremotely.com/remote-jobs.rss"],
        source_name="we_work_remotely",
        max_articles=max_articles,
        poll_interval=poll_interval,
    )


def reddit(subreddit: str, max_articles: int = 20, poll_interval: Optional[int] = None) -> RSSNormalizer:
    return RSSNormalizer(
        urls=[f"https://www.reddit.com/r/{subreddit}.rss"],
        source_name=f"reddit_{subreddit}",
        max_articles=max_articles,
        poll_interval=poll_interval,
    )
