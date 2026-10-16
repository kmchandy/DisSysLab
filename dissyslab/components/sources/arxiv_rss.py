"""arXiv listings from arXiv's own RSS feed, with the abstract and authors.

---
out: source, title, authors, abstract, text, url, timestamp
---

Why not the listing pages (``web_scraper.ArxivScraper``): a listing page
gives the title, authors and subjects, but **no abstract**. Roles told
that ``text`` held an abstract were rating papers from their titles
(paper port 6, ``docs/internals/design/officespeak_ports/arxiv_radar.md``).
The RSS feed at ``https://rss.arxiv.org/rss/<category>`` carries the
abstract in each item's description (after ``Abstract:``) and the authors
in ``dc:creator`` (checked 16 October 2026).

Each message has ``authors`` and ``abstract`` as fields of their own, and
``text`` as title, authors and abstract together, so a role written for
the five standard fields still reads the whole paper.
"""

from __future__ import annotations

from typing import Any, Optional

from dissyslab.components.sources.rss_normalizer import RSSNormalizer

FEED = "https://rss.arxiv.org/rss/{category}"


class ArxivRSS(RSSNormalizer):
    """One arXiv category's new papers, one message per paper."""

    def __init__(
        self,
        category: str,
        name: str,
        max_articles: Optional[int] = None,
        poll_interval: Optional[int] = None,
    ) -> None:
        super().__init__(
            url=FEED.format(category=category),
            name=name,
            max_articles=max_articles,
            poll_interval=poll_interval,
        )

    def _to_standard_dict(self, entry: Any, feed_url: str) -> Optional[dict]:
        base = super()._to_standard_dict(entry, feed_url)
        if base is None:
            return None
        description = base["text"]
        _, marker, after = description.partition("Abstract:")
        abstract = after.strip() if marker else description.strip()
        authors = str(entry.get("author", "") or "").strip()
        base["authors"] = authors
        base["abstract"] = abstract
        base["text"] = f"{base['title']}\nAuthors: {authors}\nAbstract: {abstract}"
        return base


def arxiv_cs_ai(max_articles: int = 20, poll_interval: Optional[int] = None) -> ArxivRSS:
    """Artificial Intelligence (cs.AI)."""
    return ArxivRSS("cs.AI", "arxiv_cs_ai", max_articles, poll_interval)


def arxiv_cs_lg(max_articles: int = 20, poll_interval: Optional[int] = None) -> ArxivRSS:
    """Machine Learning (cs.LG)."""
    return ArxivRSS("cs.LG", "arxiv_cs_lg", max_articles, poll_interval)


def arxiv_cs_cl(max_articles: int = 20, poll_interval: Optional[int] = None) -> ArxivRSS:
    """Computation and Language (cs.CL)."""
    return ArxivRSS("cs.CL", "arxiv_cs_cl", max_articles, poll_interval)


def arxiv_cs_cv(max_articles: int = 20, poll_interval: Optional[int] = None) -> ArxivRSS:
    """Computer Vision (cs.CV)."""
    return ArxivRSS("cs.CV", "arxiv_cs_cv", max_articles, poll_interval)


def arxiv_cs_ro(max_articles: int = 20, poll_interval: Optional[int] = None) -> ArxivRSS:
    """Robotics (cs.RO)."""
    return ArxivRSS("cs.RO", "arxiv_cs_ro", max_articles, poll_interval)
