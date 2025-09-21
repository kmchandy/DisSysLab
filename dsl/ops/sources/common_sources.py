# dsl/block_lib/sources/source_lib/gen_lib.py
from __future__ import annotations
import itertools
import random
import json
import glob
import csv
import time
from datetime import datetime
from typing import Any, Callable, Iterable, Iterator, Optional
from functools import wraps


# Public API
__all__ = [
    "from_list",
    "from_list_as_key",
    "from_list_as_key_with_time",
    "from_file_lines",
    "from_file_lines_as_key",
    "from_file_lines_as_key_with_time",
    "from_csv_dicts",
    "from_numpy_rows",
    "from_rss_headlines",
    "from_random_integers",
]

# ------------------------------------------------------------
# Helper used by the “..._with_time” functions.
# You can change the format in ONE place and all generators update.
# ------------------------------------------------------------


def _now_str() -> str:
    """Return current time as 'YYYY-MM-DD HH:MM:SS'."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def as_factory(f: Callable[..., Iterator[Any]]) -> Callable[..., Callable[[], Iterator[Any]]]:
    @wraps(f)
    def wrapper(*args, **kwargs) -> Callable[[], Iterator[Any]]:
        def _gen() -> Iterator[Any]:
            return f(*args, **kwargs)
        return _gen
    return wrapper

# ------------------------------------------------------------
# LIST-BASED GENERATORS
# ------------------------------------------------------------


@as_factory
def from_list(items: Iterable[Any]) -> Iterator[Any]:
    """
    Yield each element from a list (or any iterable).

    Example:
      gen = from_list(['apple', 'banana'])
      for x in gen():  # yields 'apple', 'banana'
          print(x)
    """
    for item in items:
        yield item


@as_factory
def from_list_with_delay(items: Iterable[Any], delay=None) -> Callable[[], Iterator[Any]]:
    """
    Yield each element from a list (or any iterable).

    Example:
      gen = from_list(['apple', 'banana'])
      for x in gen():  # yields 'apple', 'banana'
          print(x)
    """
    # Snapshot items once so each run of gen() yields the same values.
    snapshot = list(items)

    def _gen() -> Iterator[Any]:
        for x in snapshot:
            yield x
            if delay:
                time.sleep(delay)
    return _gen


@as_factory
def from_list_as_key(items: Iterable[Any], key: str) -> Callable[[], Iterator[dict]]:
    """
    Yield each item wrapped in a dict with the given key.

    Example:
      gen = from_list_as_key(['apple', 'banana'], key='fruit')
      # yields {'fruit': 'apple'}, {'fruit': 'banana'}
    """
    snapshot = list(items)

    def _gen() -> Iterator[dict]:
        for x in snapshot:
            yield {key: x}
    return _gen


@as_factory
def from_list_as_key_with_time(
    items: Iterable[Any],
    key: str,
    time_key: str = "time",
    now: Callable[[], str] = _now_str,
) -> Callable[[], Iterator[dict]]:
    """
    Like from_list_as_key, but also adds a timestamp string.

    Example:
      gen = from_list_as_key_with_time(['a'], key='text')
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
def from_file_lines(path: str, encoding: str = "utf-8") -> Callable[[], Iterator[str]]:
    """
    Yield each line from a text file, without the trailing newline.

    Example:
      gen = from_file_lines('notes.txt')
      # yields 'first line', 'second line', ...
    """
    def _gen() -> Iterator[str]:
        with open(path, "r", encoding=encoding) as f:
            for line in f:
                yield line.rstrip("\n")
    return _gen


def from_file_lines_as_key(
    path: str,
    key: str,
    encoding: str = "utf-8",
) -> Callable[[], Iterator[dict]]:
    """
    Yield each file line wrapped in a dict {key: line}.

    Example:
      gen = from_file_lines_as_key('notes.txt', key='text')
      # yields {'text': 'first line'}, {'text': 'second line'}, ...
    """
    def _gen() -> Iterator[dict]:
        with open(path, "r", encoding=encoding) as f:
            for line in f:
                yield {key: line.rstrip("\n")}
    return _gen


def from_file_lines_as_key_with_time(
    path: str,
    key: str,
    time_key: str = "time",
    encoding: str = "utf-8",
    now: Callable[[], str] = _now_str,
) -> Callable[[], Iterator[dict]]:
    """
    Like from_file_lines_as_key, but also adds a timestamp string.

    Example:
      gen = from_file_lines_as_key_with_time('notes.txt', key='text')
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
def from_csv_dicts(path: str, encoding: str = "utf-8") -> Callable[[], Iterator[dict]]:
    """
    Yield one dict per CSV row using the header row as keys.

    Example:
      gen = from_csv_dicts('people.csv')
      # yields {'name': 'Ada', 'age': '42'}, ...
    """
    def _gen() -> Iterator[dict]:
        with open(path, newline="", encoding=encoding) as f:
            yield from csv.DictReader(f)
    return _gen


# ------------------------------------------------------------
# NUMPY ROWS (optional; no import needed)
# ------------------------------------------------------------
def from_numpy_rows(array: Iterable[Any]) -> Callable[[], Iterator[Any]]:
    """
    Yield each row from a NumPy array (or any iterable of rows).
    No wrapping; you get the row object as-is.

    Example:
      gen = from_numpy_rows(my_array)
      for row in gen():
          ...
    """
    def _gen() -> Iterator[Any]:
        for row in array:
            yield row
    return _gen


# ------------------------------------------------------------
#           GENERATE_RANDOM_INTEGERS
# ------------------------------------------------------------

@as_factory
def from_random_integers(N: int, LOW: int, HIGH: int) -> Iterator[int]:
    import random
    for _ in range(N):
        yield random.randint(LOW, HIGH)


# ------------------------------------------------------------
# RSS HEADLINES (requires 'feedparser')
# ------------------------------------------------------------
try:
    import feedparser  # type: ignore
except Exception:
    feedparser = None  # stays None if not installed


def from_rss_headlines(
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
      gen = from_rss_headlines('https://example.com/feed', interval=10, limit=5)
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


# ------------------------------------------------------------
#    MORE EXAMPLES of generator_fn
# ------------------------------------------------------------


def from_repeat(value, times: Optional[int] = None) -> Iterator:
    it = itertools.repeat(
        value) if times is None else itertools.repeat(value, times)
    for x in it:
        yield x


def from_range(start: int, stop: Optional[int] = None, step: int = 1) -> Iterator[int]:
    # Mirrors built-in range semantics (range(stop)) if stop is None
    if stop is None:
        start, stop = 0, start
    for x in range(start, stop, step):
        yield x


def from_counter(start: int = 0, step: int = 1, times: Optional[int] = None) -> Iterator[int]:
    n = start
    i = 0
    while times is None or i < times:
        yield n
        n += step
        i += 1


def from_jsonl(path: str) -> Iterator[dict]:
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


def from_csv_rows(path: str) -> Iterator[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            yield dict(row)


def from_dir_files(pattern: str) -> Iterator[str]:
    for p in glob.iglob(pattern, recursive=True):
        yield p


def from_timer_interval(every_s: float, count: Optional[int] = None, payload=None) -> Iterator[dict]:
    i = 0
    while count is None or i < count:
        # creation time; downstream blocks should not reuse this for arrival time
        msg = {"time": _now_str()} if payload is None else {
            "time": _now_str(), "data": payload}
        yield msg
        time.sleep(every_s)
        i += 1

# ------------------------------------------------------------
#           GENERATE_RANDOM_INTEGERS
# ------------------------------------------------------------


def from_random_ints(low: int, high: int, count: Optional[int] = None) -> Iterator[int]:
    i = 0
    while count is None or i < count:
        yield random.randint(low, high)
        i += 1


def from_poll(fn: Callable[[], object], every_s: float, count: Optional[int] = None) -> Iterator:
    i = 0
    while count is None or i < count:
        yield fn()
        time.sleep(every_s)
        i += 1
