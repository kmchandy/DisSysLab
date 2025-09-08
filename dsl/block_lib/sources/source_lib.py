# dsl/block_lib/sources/gen_lib.py
from __future__ import annotations
import csv
from datetime import datetime
from typing import Any, Callable, Iterable, Iterator, Optional
import time

# Generate elements from a list
# Example items = ['apple', 'banana'],
# yields 'apple', 'banana'
# parameters
# -----------


def gen_list(items: Iterable[Any]) -> Callable[[], Iterator[Any]]:
    """Yield each element from items."""
    def _gen():
        for x in items:
            yield x
    return _gen


# Generate elements from a list, where each element is wrapped
# in a dict with a specified key.
# Example items = ['apple', 'banana'], key='fruit',
# yields {'fruit': 'apple'}, {'fruit': 'banana'}
def gen_list_as_key(items: Iterable[Any], key: str) -> Callable[[], Iterator[dict]]:
    """Yield {'<key>': item} for each element."""
    def _gen():
        for x in items:
            yield {key: x}
    return _gen


# Generate elements from a list, where each element is wrapped
# 3) List → wrap with a key + current time


def gen_list_as_key_with_time(items: Iterable[Any], key: str, time_key: str = "time") -> Callable[[], Iterator[dict]]:
    """Yield {'<key>': item, 'time': '<YYYY-MM-DD HH:MM:SS>'} per element."""
    def _gen():
        for x in items:
            yield {key: x, time_key: datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
    return _gen

# 4) File lines (stripped)


def gen_file_lines(path: str, encoding: str = "utf-8") -> Callable[[], Iterator[str]]:
    """Yield each line (rstrip '\\n') from a text file."""
    def _gen():
        with open(path, "r", encoding=encoding) as f:
            for line in f:
                yield line.rstrip("\n")
    return _gen


# 5) RSS headlines (dict messages)
try:
    import feedparser
except Exception:
    feedparser = None


def gen_rss_headlines(url: str, interval: float = 5.0, limit: Optional[int] = None) -> Callable[[], Iterator[dict]]:
    """
    Yield {'text': '<headline>', 'source': '<feed-url>'} from an RSS feed.
    Runs until limit is reached (if provided), otherwise forever with interval sleep.
    """
    if feedparser is None:
        raise RuntimeError(
            "feedparser not installed. pip install 'feedparser>=6.0.0'")

    def _gen():
        seen = set()
        n = 0
        while True:
            feed = feedparser.parse(url)
            for entry in getattr(feed, "entries", []):
                title = getattr(entry, "title", None) or entry.get(
                    "title") or ""
                if not title or title in seen:
                    continue
                seen.add(title)
                yield {"text": title, "source": getattr(feed, "href", url)}
                n += 1
                if limit is not None and n >= limit:
                    return
            time.sleep(interval)
    return _gen


# 6) CSV rows as dicts (optional)


def gen_csv_dicts(path: str, encoding: str = "utf-8") -> Callable[[], Iterator[dict]]:
    """Yield one dict per CSV row using the header row as keys."""
    def _gen():
        with open(path, newline="", encoding=encoding) as f:
            for row in csv.DictReader(f):
                yield row
    return _gen

# 7) NumPy rows (for ML pipelines; no dicts)


def gen_numpy_rows(array) -> Callable[[], Iterator[Any]]:
    """Yield each row from a NumPy array (no wrapping)."""
    def _gen():
        for row in array:
            yield row
    return _gen
