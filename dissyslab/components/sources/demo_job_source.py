# dissyslab/components/sources/demo_job_source.py

"""
Demo Job Source — produces fake job postings for Module 05.

Usage:
    from dissyslab.components.sources.demo_job_source import DemoJobSource
    from examples.module_05.demo_job_source import DEMO_JOB_FEEDS

    src = DemoJobSource(feed_name="python_jobs")
    posting = src.run()   # returns a string, or None when exhausted

Mirrors the RSSSource interface exactly — swap one for the other
in app_live.py to move from demo data to real RSS feeds.
"""

from examples.module_05.demo_job_source import DEMO_JOB_FEEDS


class DemoJobSource:
    """
    Produces demo job postings one at a time, returns None when exhausted.

    Args:
        feed_name:    Key into DEMO_JOB_FEEDS ("python_jobs" or "ml_jobs")
        max_articles: Stop after this many postings (default: all of them)

    Each call to .run() returns the next posting as a string.
    Returns None when all postings have been returned.
    """

    def __init__(self, feed_name: str, max_articles: int = None):
        self.articles = list(DEMO_JOB_FEEDS[feed_name])
        self.max_articles = max_articles or len(self.articles)
        self.index = 0

    def run(self):
        if self.index >= min(len(self.articles), self.max_articles):
            return None
        article = self.articles[self.index]
        self.index += 1
        return article
