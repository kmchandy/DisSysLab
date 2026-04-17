# components/sources/web_scraper.py

"""
WebScraper and ArxivScraper: scrape web pages and produce standard article dicts.

Use these for sites that don't offer RSS feeds. Both produce the same standard
five-key article dict used throughout DisSysLab:

    {
        "source":    str,   # site name
        "title":     str,   # article headline or paper title
        "text":      str,   # plain text content
        "url":       str,   # link to article or paper
        "timestamp": str,   # date string or "" if unavailable
    }

─────────────────────────────────────────────────────────────────────────────
WebScraper — generic CSS-selector scraper for simple static HTML sites
─────────────────────────────────────────────────────────────────────────────

Usage:
    from dissyslab.components.sources.web_scraper import WebScraper
    from dissyslab.blocks import Source

    scraper = WebScraper(
        url="https://example.com/news",
        source_name="example",
        article_selector="article.post",   # CSS selector for each article
        title_selector="h2.title",         # within each article
        link_selector="a.read-more",       # within each article
        text_selector="p.summary",         # within each article
        date_selector="time",              # within each article (optional)
        max_articles=20,
        poll_interval=3600,                # None = one-shot
    )
    source = Source(fn=scraper.run, name="example")

─────────────────────────────────────────────────────────────────────────────
ArxivScraper — dedicated scraper for arxiv.org listing pages
─────────────────────────────────────────────────────────────────────────────

arXiv uses a definition-list HTML structure that requires custom parsing.
Use ArxivScraper (or its convenience factory functions) instead of WebScraper
for any arxiv.org/list/* URL.

Usage:
    from dissyslab.components.sources.web_scraper import arxiv_cs_ai
    from dissyslab.blocks import Source

    feed   = arxiv_cs_ai(max_articles=20, poll_interval=3600)
    source = Source(fn=feed.run, name="arxiv_cs_ai")

Available factory functions:
    arxiv_cs_ai()   — Artificial Intelligence (cs.AI)
    arxiv_cs_lg()   — Machine Learning (cs.LG)
    arxiv_cs_cl()   — Computation and Language (cs.CL)
    arxiv_cs_cv()   — Computer Vision (cs.CV)
    arxiv_cs_ro()   — Robotics (cs.RO)

arXiv updates once daily (around 8pm Eastern). A poll_interval of 3600
(hourly) is more than sufficient — duplicate papers are automatically
filtered by URL.
"""

import time
from typing import Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


# ── WebScraper ────────────────────────────────────────────────────────────────

class WebScraper:
    """
    Generic scraper for simple static HTML sites.

    Uses CSS selectors to locate article containers and extract title,
    link, text, and optional date from each one.

    Args:
        url:              URL of the page listing articles
        source_name:      Human-readable name (e.g. "ars_technica")
        article_selector: CSS selector for each article container
        title_selector:   CSS selector for the title, within each article
        link_selector:    CSS selector for the link, within each article
        text_selector:    CSS selector for the body text, within each article
        date_selector:    CSS selector for the date, within each article (optional)
        max_articles:     Max articles per fetch (None = all)
        poll_interval:    Re-fetch every N seconds (None = one-shot)
        headers:          Optional HTTP headers dict
    """

    DEFAULT_HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (compatible; DisSysLab/1.0; "
            "+https://github.com/kmchandy/DisSysLab)"
        )
    }

    def __init__(
        self,
        url: str,
        source_name: str = "web",
        article_selector: str = "article",
        title_selector: str = "h2",
        link_selector: str = "a",
        text_selector: str = "p",
        date_selector: Optional[str] = None,
        max_articles: Optional[int] = None,
        poll_interval: Optional[int] = None,
        headers: Optional[dict] = None,
    ):
        self.url = url
        self.source_name = source_name
        self.article_selector = article_selector
        self.title_selector = title_selector
        self.link_selector = link_selector
        self.text_selector = text_selector
        self.date_selector = date_selector
        self.max_articles = max_articles
        self.poll_interval = poll_interval
        self.headers = headers or self.DEFAULT_HEADERS
        self._seen_urls = set()

    def run(self):
        """
        Generator: yields one standard dict per article.
        Compatible with Source(fn=scraper.run, name="...").
        """
        if self.poll_interval:
            while True:
                yield from self._fetch()
                print(f"[{self.source_name}] Sleeping {self.poll_interval}s...")
                time.sleep(self.poll_interval)
        else:
            yield from self._fetch()

    def _fetch(self):
        try:
            print(f"[{self.source_name}] Fetching {self.url}...")
            response = requests.get(self.url, headers=self.headers, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")

            articles = soup.select(self.article_selector)
            if self.max_articles:
                articles = articles[:self.max_articles]

            print(f"[{self.source_name}] {len(articles)} items found")

            for element in articles:
                article = self._to_standard_dict(element)
                if article is None:
                    continue
                if article["url"] in self._seen_urls:
                    continue
                self._seen_urls.add(article["url"])
                yield article

        except Exception as e:
            print(f"[{self.source_name}] Error fetching {self.url}: {e}")

    def _to_standard_dict(self, element) -> Optional[dict]:
        title_el = element.select_one(self.title_selector)
        title = title_el.get_text(strip=True) if title_el else ""

        link_el = element.select_one(self.link_selector)
        if link_el:
            href = link_el.get("href", "")
            url = urljoin(self.url, href)
        else:
            url = self.url

        text_el = element.select_one(self.text_selector)
        text = text_el.get_text(strip=True) if text_el else ""

        if not text:
            text = title
        if not title:
            title = text[:80]
        if not text.strip():
            return None

        timestamp = ""
        if self.date_selector:
            date_el = element.select_one(self.date_selector)
            if date_el:
                timestamp = (
                    date_el.get("datetime", "") or date_el.get_text(strip=True)
                )

        return {
            "source":    self.source_name,
            "title":     title,
            "text":      text,
            "url":       url,
            "timestamp": timestamp,
        }


# ── WebScraper convenience factory functions ──────────────────────────────────

def ars_technica(
    max_articles: int = 20, poll_interval: Optional[int] = None
) -> WebScraper:
    return WebScraper(
        url="https://arstechnica.com",
        source_name="ars_technica",
        article_selector="article",
        title_selector="h2",
        link_selector="a[href]",
        text_selector="p",
        date_selector="time",
        max_articles=max_articles,
        poll_interval=poll_interval,
    )


def wired(
    max_articles: int = 20, poll_interval: Optional[int] = None
) -> WebScraper:
    return WebScraper(
        url="https://www.wired.com/most-recent",
        source_name="wired",
        article_selector="div.summary-item",
        title_selector="h3",
        link_selector="a",
        text_selector="p.summary-item__dek",
        date_selector="time",
        max_articles=max_articles,
        poll_interval=poll_interval,
    )


def github_trending(
    max_articles: int = 20, poll_interval: Optional[int] = None
) -> WebScraper:
    return WebScraper(
        url="https://github.com/trending",
        source_name="github_trending",
        article_selector="article.Box-row",
        title_selector="h2",
        link_selector="a",
        text_selector="p",
        date_selector=None,
        max_articles=max_articles,
        poll_interval=poll_interval,
    )


# ── ArxivScraper ──────────────────────────────────────────────────────────────

class ArxivScraper:
    """
    Dedicated scraper for arxiv.org listing pages.

    arXiv uses a definition-list HTML structure that requires custom parsing
    rather than generic CSS selectors. This class handles that structure and
    produces the standard five-key article dict.

    The `text` field contains: title + authors + subjects — this gives AI
    agents enough context to filter and classify papers accurately.

    Args:
        subject:       arXiv subject code, e.g. "cs.AI", "cs.LG", "cs.CL"
        source_name:   Human-readable name, e.g. "arxiv_cs_ai"
        max_articles:  Max papers per fetch (None = all)
        poll_interval: Re-fetch every N seconds (None = one-shot)

    arXiv updates once daily around 8pm Eastern. poll_interval=3600 (hourly)
    is sufficient — duplicate papers are filtered automatically by URL.
    """

    BASE_URL = "https://arxiv.org/list/{subject}/recent"

    DEFAULT_HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (compatible; DisSysLab/1.0; "
            "+https://github.com/kmchandy/DisSysLab)"
        )
    }

    def __init__(
        self,
        subject: str,
        source_name: str,
        max_articles: Optional[int] = None,
        poll_interval: Optional[int] = None,
    ):
        self.subject = subject
        self.source_name = source_name
        self.url = self.BASE_URL.format(subject=subject)
        self.max_articles = max_articles
        self.poll_interval = poll_interval
        self._seen_urls = set()

    def run(self):
        """
        Generator: yields one standard dict per paper.
        Compatible with Source(fn=scraper.run, name="...").
        """
        if self.poll_interval:
            while True:
                yield from self._fetch()
                print(f"[{self.source_name}] Sleeping {self.poll_interval}s...")
                time.sleep(self.poll_interval)
        else:
            yield from self._fetch()

    def _fetch(self):
        try:
            print(f"[{self.source_name}] Fetching {self.url}...")
            response = requests.get(
                self.url, headers=self.DEFAULT_HEADERS, timeout=15
            )
            response.raise_for_status()
            papers = self._parse(response.text)
            print(f"[{self.source_name}] {len(papers)} papers found")

            for paper in papers:
                if paper["url"] in self._seen_urls:
                    continue
                self._seen_urls.add(paper["url"])
                yield paper

        except Exception as e:
            print(f"[{self.source_name}] Error fetching {self.url}: {e}")

    def _parse(self, html: str) -> list:
        """
        Parse the arXiv listing page HTML.

        arXiv uses a <dl> list where each paper occupies a <dt>/<dd> pair:
          <dt> — contains the arXiv ID and links
          <dd> — contains title, authors, subjects
        """
        soup = BeautifulSoup(html, "html.parser")
        dl = soup.find("dl")
        if not dl:
            return []

        dts = dl.find_all("dt")
        dds = dl.find_all("dd")

        papers = []
        for dt, dd in zip(dts, dds):

            # ── URL ───────────────────────────────────────────────────────
            abs_link = dt.find("a", href=lambda h: h and h.startswith("/abs/"))
            if not abs_link:
                continue
            url = "https://arxiv.org" + abs_link["href"]

            # ── Title ─────────────────────────────────────────────────────
            title_div = dd.find("div", class_="list-title")
            if title_div:
                # Remove the "Title:" label span if present
                for span in title_div.find_all("span", class_="descriptor"):
                    span.decompose()
                title = title_div.get_text(strip=True)
            else:
                title = ""

            # ── Authors ───────────────────────────────────────────────────
            authors_div = dd.find("div", class_="list-authors")
            if authors_div:
                authors = authors_div.get_text(strip=True)
                # Remove the "Authors:" label
                authors = authors.replace("Authors:", "").strip()
            else:
                authors = ""

            # ── Subjects ──────────────────────────────────────────────────
            subjects_div = dd.find("div", class_="list-subjects")
            if subjects_div:
                subjects = subjects_div.get_text(strip=True)
                subjects = subjects.replace("Subjects:", "").strip()
            else:
                subjects = ""

            # ── Compose text field for AI agents ─────────────────────────
            # Combine all fields — gives agents full context for filtering
            text = f"{title}\nAuthors: {authors}\nSubjects: {subjects}"

            if not title:
                continue

            papers.append({
                "source":    self.source_name,
                "title":     title,
                "text":      text,
                "url":       url,
                "timestamp": "",
            })

            if self.max_articles and len(papers) >= self.max_articles:
                break

        return papers


# ── ArxivScraper convenience factory functions ────────────────────────────────

def arxiv_cs_ai(
    max_articles: int = 20, poll_interval: Optional[int] = None
) -> ArxivScraper:
    """Artificial Intelligence — https://arxiv.org/list/cs.AI/recent"""
    return ArxivScraper(
        subject="cs.AI",
        source_name="arxiv_cs_ai",
        max_articles=max_articles,
        poll_interval=poll_interval,
    )


def arxiv_cs_lg(
    max_articles: int = 20, poll_interval: Optional[int] = None
) -> ArxivScraper:
    """Machine Learning — https://arxiv.org/list/cs.LG/recent"""
    return ArxivScraper(
        subject="cs.LG",
        source_name="arxiv_cs_lg",
        max_articles=max_articles,
        poll_interval=poll_interval,
    )


def arxiv_cs_cl(
    max_articles: int = 20, poll_interval: Optional[int] = None
) -> ArxivScraper:
    """Computation and Language — https://arxiv.org/list/cs.CL/recent"""
    return ArxivScraper(
        subject="cs.CL",
        source_name="arxiv_cs_cl",
        max_articles=max_articles,
        poll_interval=poll_interval,
    )


def arxiv_cs_cv(
    max_articles: int = 20, poll_interval: Optional[int] = None
) -> ArxivScraper:
    """Computer Vision — https://arxiv.org/list/cs.CV/recent"""
    return ArxivScraper(
        subject="cs.CV",
        source_name="arxiv_cs_cv",
        max_articles=max_articles,
        poll_interval=poll_interval,
    )


def arxiv_cs_ro(
    max_articles: int = 20, poll_interval: Optional[int] = None
) -> ArxivScraper:
    """Robotics — https://arxiv.org/list/cs.RO/recent"""
    return ArxivScraper(
        subject="cs.RO",
        source_name="arxiv_cs_ro",
        max_articles=max_articles,
        poll_interval=poll_interval,
    )
