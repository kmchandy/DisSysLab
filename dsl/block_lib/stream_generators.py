"""
stream_generators.py

Generator blocks that emit messages into a distributed network.

Classes:
- StreamGenerator
- GenerateFromURL
- GenerateFromRSS

Functions:
- generate(source, delay=None, key="data", label=None, include_time=False, name=None)
- GenerateFromList(...)
- GenerateFromFile(...)
- GenerateFromFunction(...)
"""

from __future__ import annotations
import time
import types
import requests
import traceback
from rich import print as rprint
from bs4 import BeautifulSoup
from datetime import datetime
from typing import Optional, Union, Callable, Any, Iterable, Sequence
from dsl.core import SimpleAgent

# =================================================
#                StreamGenerator                   |
# =================================================


class StreamGenerator(SimpleAgent):
    """
    Emits messages from a Python generator function.
    Each yielded message is sent to the 'out' port; '__STOP__' is sent at the end.
    """

    def __init__(self, name=None, generator_fn=None, delay: Optional[float] = None, *args, **kwargs):
        if generator_fn is None:
            raise ValueError("StreamGenerator requires a generator_fn")

        def run(agent):
            try:
                for msg in generator_fn(*args, **kwargs):
                    agent.send(msg, "out")
                    if delay:
                        time.sleep(delay)
                agent.send("__STOP__", "out")
            except Exception as e:
                rprint("[bold red]❌ StreamGenerator error:[/bold red] " + str(e))
                with open("dsl_debug.log", "a") as log:
                    log.write("\n--- StreamGenerator Error ---\n")
                    log.write(traceback.format_exc())
                raise

        # Note: SimpleAgent signature in your project: (name, inport?, outports, handle_msg?, run?)
        super().__init__(name=name or "StreamGenerator",
                         outports=["out"], run=run)

# =================================================
#                    generate                      |
# =================================================


def generate(source=None, delay: Optional[float] = None, key: Optional[str] = "data",
             label: Optional[str] = None, include_time: bool = False, name: Optional[str] = None,
             *args, **kwargs):
    """
    Create a StreamGenerator from a list, a generator function, or a callable that returns one.
    """

    def wrap_as_dict(item):
        if key is None:
            return item
        msg = {key: item}
        if label:
            msg["source"] = label
        if include_time:
            msg["time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return msg

    if name is None:
        kind = "list" if isinstance(
            source, list) else "callable" if callable(source) else "unknown"
        name = f"generate_from_{kind}"

    if isinstance(source, list):
        def list_generator():
            for item in source:
                yield wrap_as_dict(item)
        return StreamGenerator(name=name, generator_fn=list_generator, delay=delay)

    if callable(source):
        def wrapped_generator():
            result = source(*args, **kwargs)
            if isinstance(result, types.GeneratorType) or isinstance(result, list):
                for item in result:
                    yield wrap_as_dict(item)
            else:
                raise TypeError(
                    f"Callable must return list or generator, got {type(result)}")
        return StreamGenerator(name=name, generator_fn=wrapped_generator, delay=delay)

    raise TypeError(
        "Unsupported source type; pass a list or a callable returning a list/generator.")

# =================================================
#              GenerateFromURL                     |
# =================================================


class GenerateFromURL(StreamGenerator):
    """
    Stream text content from a webpage as dictionary messages:
      {key: chunk, "source": label?, "time": ...?}
    """

    @staticmethod
    def _fetch_text_chunks(url: str, split: str = "paragraph"):
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "lxml")
        paragraphs = soup.find_all("p")
        text = "\n".join(p.get_text().strip()
                         for p in paragraphs if p.get_text().strip())
        if split == "sentence":
            import re
            for s in re.split(r"(?<=[.!?]) +", text):
                s = s.strip()
                if s:
                    yield s
        else:
            for p in text.split("\n"):
                p = p.strip()
                if p:
                    yield p

    def __init__(self, url: str, split: str = "paragraph", delay: Optional[Union[int, float]] = None,
                 key: str = "data", label: Optional[str] = None, include_time: bool = False,
                 name: Optional[str] = None, description: Optional[str] = None):
        # Closure captures url/split; StreamGenerator will just call it.
        def dict_generator():
            try:
                for chunk in self._fetch_text_chunks(url, split):
                    msg = {key: chunk}
                    if label:
                        msg["source"] = label
                    if include_time:
                        msg["time"] = datetime.now().strftime(
                            "%Y-%m-%d %H:%M:%S")
                    yield msg
            except Exception as e:
                rprint(f"⚠️ Error fetching {url}: {e}")
                yield {"error": f"Error fetching {url}: {e}"}

        super().__init__(name=name or "GenerateFromURL",
                         generator_fn=dict_generator, delay=delay)

# =================================================
#              GenerateFromList                    |
# =================================================


def GenerateFromList(*, items: Sequence[Any] | Iterable[Any], delay: Optional[float] = None,
                     key: Optional[str] = None, label: Optional[str] = None, include_time: bool = False,
                     name: Optional[str] = None, **kwargs):
    """Create a StreamGenerator from a Python list or iterable."""
    return generate(source=list(items), delay=delay, key=key, label=label,
                    include_time=include_time, name=name, **kwargs)

# =================================================
#              GenerateFromFile                    |
# =================================================


def GenerateFromFile(*, path: str, delay: Optional[float] = None, key: Optional[str] = None,
                     label: Optional[str] = None, include_time: bool = False, name: Optional[str] = None,
                     encoding: str = "utf-8", line_by_line: bool = True, **kwargs):
    """
    Create a StreamGenerator from a file. If line_by_line, emits one line per message.
    """

    def file_iter():
        with open(path, "r", encoding=encoding) as f:
            if line_by_line:
                for line in f:
                    yield line.rstrip("\n")
            else:
                yield f.read()

    return generate(source=file_iter, delay=delay, key=key, label=label,
                    include_time=include_time, name=name, **kwargs)

# =================================================
#              GenerateFromFunction                |
# =================================================


def GenerateFromFunction(*, fn: Callable[..., Any], delay: Optional[float] = None, key: Optional[str] = None,
                         label: Optional[str] = None, include_time: bool = False, name: Optional[str] = None,
                         args: Sequence[Any] = (), fn_kwargs: Optional[dict[str, Any]] = None, **kwargs):
    """
    Create a StreamGenerator from a Python function (fn(*args, **fn_kwargs)).
    """

    def call_fn():
        return fn(*args, **(fn_kwargs or {}))

    return generate(source=call_fn, delay=delay, key=key, label=label,
                    include_time=include_time, name=name, **kwargs)

# =================================================
#                GenerateFromRSS                   |
# =================================================


try:
    import feedparser
except Exception:
    feedparser = None


class GenerateFromRSS(SimpleAgent):
    """
    Stream headlines from an RSS feed as dicts with the standard 'text' key.
    Emits: {'text': '<headline>', 'source': '<feed-url>', 'time': <epoch>}
    """

    def __init__(self, url: str, interval: float = 5.0, limit: Optional[int] = None, name: Optional[str] = None):
        super().__init__(name=name or "GenerateFromRSS",
                         outports=["out"], run=self.run)
        self.url = url
        self.interval = interval
        self.limit = limit
        self._seen = set()
        if feedparser is None:
            raise RuntimeError(
                "feedparser is not installed. Install with: pip install 'feedparser>=6.0.0'")

    def run(self):
        count = 0
        while True:
            feed = feedparser.parse(self.url)
            now = time.time()
            for entry in getattr(feed, "entries", []):
                title = getattr(entry, "title", None) or entry.get(
                    "title") or ""
                if not title or title in self._seen:
                    continue
                self._seen.add(title)
                self.send({"text": title, "source": getattr(
                    feed, "href", self.url), "time": now}, "out")
                count += 1
                if self.limit is not None and count >= self.limit:
                    self.send("__STOP__", "out")
                    return
            time.sleep(self.interval)


__all__ = [
    "StreamGenerator",
    "generate",
    "GenerateFromURL",
    "GenerateFromList",
    "GenerateFromFile",
    "GenerateFromFunction",
    "GenerateFromRSS",
]
