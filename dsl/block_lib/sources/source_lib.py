# dsl/block_lib/sources/gen_lib.py
from __future__ import annotations

import csv
import time
from datetime import datetime
from typing import Any, Callable, Iterable, Iterator, Optional

# Public API
__all__ = [
    "gen_list",
    "gen_list_as_key",
    "gen_list_as_key_with_time",
    "gen_file_lines",
    "gen_file_lines_as_key",
    "gen_file_lines_as_key_with_time",
    "gen_csv_dicts",
    "gen_numpy_rows",
    "gen_rss_headlines",
]

# ------------------------------------------------------------
# Helper used by the “..._with_time” functions.
# You can change the format in ONE place and all generators update.
# ------------------------------------------------------------


def _now_str() -> str:
    """Return current time as 'YYYY-MM-DD HH:MM:SS'."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ------------------------------------------------------------
# LIST-BASED GENERATORS
# ------------------------------------------------------------
def gen_list(items: Iterable[Any]) -> Callable[[], Iterator[Any]]:
    """
    Yield each element from a list (or any iterable).

    Example:
      gen = gen_list(['apple', 'banana'])
      for x in gen():  # yields 'apple', 'banana'
          print(x)
    """
    # Snapshot items once so each run of gen() yields the same values.
    snapshot = list(items)

    def _gen() -> Iterator[Any]:
        for x in snapshot:
            yield x
    return _gen


def gen_list_as_key(items: Iterable[Any], key: str) -> Callable[[], Iterator[dict]]:
    """
    Yield each item wrapped in a dict with the given key.

    Example:
      gen = gen_list_as_key(['apple', 'banana'], key='fruit')
      # yields {'fruit': 'apple'}, {'fruit': 'banana'}
    """
    snapshot = list(items)

    def _gen() -> Iterator[dict]:
        for x in snapshot:
            yield {key: x}
    return _gen


def gen_list_as_key_with_time(
    items: Iterable[Any],
    key: str,
    time_key: str = "time",
    now: Callable[[], str] = _now_str,
) -> Callable[[], Iterator[dict]]:
    """
    Like gen_list_as_key, but also adds a timestamp string.

    Example:
      gen = gen_list_as_key_with_time(['a'], key='text')
      # yields {'text': 'a', 'time': '2025-09-08 12:34:56'}
    """
    snapshot = list(items)

    def _gen() -> Iterator[dict]:
        for x in snapshot:
            yield {key: x, time_key: now()}
    return _gen


# ------------------------------------------------------------
# FILE-LINE GENERATORS
# ------------------------------------------------------------
def gen_file_lines(path: str, encoding: str = "utf-8") -> Callable[[], Iterator[str]]:
    """
    Yield each line from a text file, without the trailing newline.

    Example:
      gen = gen_file_lines('notes.txt')
      # yields 'first line', 'second line', ...
    """
    def _gen() -> Iterator[str]:
        with open(path, "r", encoding=encoding) as f:
            for line in f:
                yield line.rstrip("\n")
    return _gen


def gen_file_lines_as_key(
    path: str,
    key: str,
    encoding: str = "utf-8",
) -> Callable[[], Iterator[dict]]:
    """
    Yield each file line wrapped in a dict {key: line}.

    Example:
      gen = gen_file_lines_as_key('notes.txt', key='text')
      # yields {'text': 'first line'}, {'text': 'second line'}, ...
    """
    def _gen() -> Iterator[dict]:
        with open(path, "r", encoding=encoding) as f:
            for line in f:
                yield {key: line.rstrip("\n")}
    return _gen


def gen_file_lines_as_key_with_time(
    path: str,
    key: str,
    time_key: str = "time",
    encoding: str = "utf-8",
    now: Callable[[], str] = _now_str,
) -> Callable[[], Iterator[dict]]:
    """
    Like gen_file_lines_as_key, but also adds a timestamp string.

    Example:
      gen = gen_file_lines_as_key_with_time('notes.txt', key='text')
      # yields {'text': 'first line', 'time': '2025-09-08 12:34:56'}, ...
    """
    def _gen() -> Iterator[dict]:
        with open(path, "r", encoding=encoding) as f:
            for line in f:
                yield {key: line.rstrip("\n"), time_key: now()}
    return _gen


# ------------------------------------------------------------
# CSV ROWS -> DICTS
# ------------------------------------------------------------
def gen_csv_dicts(path: str, encoding: str = "utf-8") -> Callable[[], Iterator[dict]]:
    """
    Yield one dict per CSV row using the header row as keys.

    Example:
      gen = gen_csv_dicts('people.csv')
      # yields {'name': 'Ada', 'age': '42'}, ...
    """
    def _gen() -> Iterator[dict]:
        with open(path, newline="", encoding=encoding) as f:
            yield from csv.DictReader(f)
    return _gen


# ------------------------------------------------------------
# NUMPY ROWS (optional; no import needed)
# ------------------------------------------------------------
def gen_numpy_rows(array: Iterable[Any]) -> Callable[[], Iterator[Any]]:
    """
    Yield each row from a NumPy array (or any iterable of rows).
    No wrapping; you get the row object as-is.

    Example:
      gen = gen_numpy_rows(my_array)
      for row in gen():
          ...
    """
    def _gen() -> Iterator[Any]:
        for row in array:
            yield row
    return _gen


# ------------------------------------------------------------
# RSS HEADLINES (requires 'feedparser')
# ------------------------------------------------------------
try:
    import feedparser  # type: ignore
except Exception:
    feedparser = None  # stays None if not installed


def gen_rss_headlines(
    url: str,
    interval: float = 5.0,
    limit: Optional[int] = None,
    *,
    sleep: Callable[[float], None] = time.sleep,
    parser: Optional[Callable[[str], Any]] = None,
) -> Callable[[], Iterator[dict]]:
    """
    Yield {'text': '<headline>', 'source': '<feed-url>'} from an RSS feed.

    - Checks the feed every `interval` seconds.
    - Skips duplicates.
    - Stops after `limit` headlines if `limit` is given.

    You can pass your own `parser` (for tests). By default it uses `feedparser.parse`.
    You can also pass your own `sleep` (for tests). By default it uses time.sleep.

    Example:
      gen = gen_rss_headlines('https://example.com/feed', interval=10, limit=5)
      for msg in gen():
          print(msg['text'])
    """
    if parser is None:
        if feedparser is None:
            raise RuntimeError(
                "feedparser not installed. Try: pip install 'feedparser>=6.0.0'")
        parser = feedparser.parse  # type: ignore

    def _gen() -> Iterator[dict]:
        seen: set[str] = set()
        yielded = 0
        while True:
            feed = parser(url)
            entries = getattr(feed, "entries", []) or getattr(
                feed, "items", [])
            for entry in entries:
                # entry may be an object or dict
                title = getattr(entry, "title", None) or (
                    entry.get("title") if isinstance(entry, dict) else None) or ""
                if not title or title in seen:
                    continue
                seen.add(title)
                src = getattr(feed, "href", None) or getattr(feed, "feed", {}).get(
                    "link", None) if isinstance(feed, dict) else None
                yield {"text": title, "source": src or url}
                yielded += 1
                if limit is not None and yielded >= limit:
                    return
            sleep(interval)
    return _gen
