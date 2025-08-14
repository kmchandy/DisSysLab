"""
stream_generators.py

This module defines generator blocks for emitting messages into a distributed network.
The core class is StreamGenerator. It also includes the `generate(...)` helper function
for creating generator blocks from lists or callables, and a web-based generator.

Classes:
- StreamGenerator
- GenerateTextFromURL

Functions:
- generate(source, delay=None, key="data", label=None, include_time=False, name=None)

tags: source, stream, generator, data, text, time-series
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
    StreamGenerator

    Emits messages from a Python generator function.

    Parameters:
    - name: Optional name for the block
    - generator_fn: A generator function that yields messages
    - delay: Optional delay (in seconds) between messages

    Behavior:
    - Sends each yielded message to the "out" port
    - Sends "__STOP__" after the generator is exhausted
    - On failure, prints error using `rich` and logs to 'dsl_debug.log'

    tags: ["generator", "source", "stream", "error-handling"]
    """

    def __init__(self, name=None, generator_fn=None, delay=None, *args, **kwargs):
        if generator_fn is None:
            raise ValueError("StreamGenerator requires a generator_fn")

        def init_fn(agent):
            try:
                for msg in generator_fn(*args, **kwargs):
                    agent.send(msg, "out")
                    if delay:
                        time.sleep(delay)
                agent.send("__STOP__", "out")

            except Exception as e:
                rprint(
                    f"[bold red]\u274c StreamGenerator error:[/bold red] {e}")
                with open("dsl_debug.log", "a") as log:
                    log.write("\n--- StreamGenerator Error ---\n")
                    log.write(traceback.format_exc())
                raise

        super().__init__(
            name=name or "StreamGenerator",
            description="Generate stream from Python generator",
            outports=["out"],
            init_fn=init_fn
        )

# =================================================
#                    generate                      |
# =================================================


def generate(source=None, delay=None, key=None, label=None, include_time=False, name=None, *args, **kwargs):
    """
    Create a StreamGenerator block from a list, generator, or a function returning one.

    Parameters:
    - source: list | generator function | callable returning list/generator
    - delay: Optional delay between messages
    - key: The dict key for the data in each message (default="data")
    - label: Optional string label to include as 'source' in each message
    - include_time: Whether to include a 'time' field in each message
    - name: Optional block name

    Returns:
    - StreamGenerator instance
    """

    def wrap_as_dict(item):
        if not key:
            return item
        msg = {key: item}
        if label:
            msg["source"] = label
        if include_time:
            msg["time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return msg

    if name is None:
        kind = (
            "list" if isinstance(source, list) else
            "callable" if callable(source) else
            "unknown"
        )
        name = f"generate_from_{kind}"

    if isinstance(source, list):
        def list_generator():
            for item in source:
                yield wrap_as_dict(item)
        return StreamGenerator(
            name=name,
            generator_fn=list_generator,
            delay=delay
        )

    if callable(source):
        def wrapped_generator():
            result = source(*args, **kwargs)
            if isinstance(result, types.GeneratorType) or isinstance(result, list):
                for item in result:
                    yield wrap_as_dict(item)
            else:
                raise TypeError(
                    f"Callable must return list or generator, got {type(result)}")

        return StreamGenerator(
            name=name,
            generator_fn=wrapped_generator,
            delay=delay
        )

    raise TypeError(
        f"Unsupported source type: {type(source).__name__}. "
        f"'generate(...)' accepts a list, a generator function, or a callable returning one."
    )


# =================================================
#              GenerateFromURL                 |
# =================================================


class GenerateFromURL(StreamGenerator):
    """
    A block that streams text content from a webpage as dictionary messages.

    Parameters:
    - url: A publicly readable URL.
    - split: Either 'paragraph' or 'sentence'.
    - delay: Optional time delay between emissions.
    - key: The dict key under which to store each chunk (default = 'data').
    - label: Optional label stored as 'source' in each message.
    - include_time: Whether to include a 'time' field in each message.
    - name: Optional block name.
    - description: Optional description.

    Behavior:
    - Fetches visible text via requests + BeautifulSoup.
    - Splits content and emits messages like {"data": ..., "source": ..., "time": ...}
    - Sends '__STOP__' after streaming is complete.

    Example:
    >>> block = GenerateTextFromURL("https://en.wikipedia.org/wiki/AI", split="paragraph", label="Wikipedia", include_time=True)
    """

    @staticmethod
    def _fetch_text_from_url(url: str, split: str = "paragraph"):
        try:
            response = requests.get(url)
            soup = BeautifulSoup(response.text, 'lxml')
            paragraphs = soup.find_all('p')
            text = "\n".join(p.get_text().strip()
                             for p in paragraphs if p.get_text().strip())

            if split == "sentence":
                import re
                return (s.strip() for s in re.split(r'(?<=[.!?]) +', text) if s.strip())
            else:
                return (p.strip() for p in text.split('\n') if p.strip())
        except Exception as e:
            print(f"\u26a0\ufe0f Error fetching {url}: {e}")
            yield f"[ERROR fetching URL: {e}]"

    def __init__(
        self,
        url: str,
        split: str = "paragraph",
        delay: Optional[Union[int, float]] = None,
        key: str = "data",
        label: Optional[str] = None,
        include_time: bool = False,
        name: Optional[str] = None,
        description: Optional[str] = None,
    ):
        def dict_generator(url: str, split: str = "paragraph"):
            for chunk in self._fetch_text_from_url(url, split):
                msg = {key: chunk}
                if label:
                    msg["source"] = label
                if include_time:
                    msg["time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                yield msg

        super().__init__(
            name=name or "GenerateTextFromURL",
            description=description or f"Streams text from URL: {url}",
            generator_fn=dict_generator,
            kwargs={"url": url, "split": split},
            delay=delay,
        )


__all__ = [
    "GenerateFromList",
    "GenerateFromFile",
    "GenerateFromFunction",
]


def GenerateFromList(
    *,
    items: Sequence[Any] | Iterable[Any],
    delay: Optional[float] = None,
    key: Optional[str] = None,
    label: Optional[str] = None,
    include_time: bool = False,
    name: Optional[str] = None,
    **kwargs,
):
    """
    Create a StreamGenerator from a Python list or iterable.

    Parameters match `generate(...)` for student clarity.
    """
    return generate(
        source=items,
        delay=delay,
        key=key,
        label=label,
        include_time=include_time,
        name=name,
        **kwargs,
    )


def GenerateFromFile(
    *,
    path: str,
    delay: Optional[float] = None,
    key: Optional[str] = None,
    label: Optional[str] = None,
    include_time: bool = False,
    name: Optional[str] = None,
    encoding: str = "utf-8",
    line_by_line: bool = True,
    **kwargs,
):
    """
    Create a StreamGenerator from a file.
    """
    return generate(
        source=path,
        delay=delay,
        key=key,
        label=label,
        include_time=include_time,
        name=name,
        encoding=encoding,
        line_by_line=line_by_line,
        **kwargs,
    )


def GenerateFromFunction(
    *,
    fn: Callable[..., Any],
    delay: Optional[float] = None,
    key: Optional[str] = None,
    label: Optional[str] = None,
    include_time: bool = False,
    name: Optional[str] = None,
    args: Sequence[Any] = (),
    fn_kwargs: Optional[dict[str, Any]] = None,
    **kwargs,
):
    """
    Create a StreamGenerator from a Python function.
    """
    return generate(
        source=fn,
        delay=delay,
        key=key,
        label=label,
        include_time=include_time,
        name=name,
        args=args,
        kwargs=fn_kwargs or {},
        *var_args,
        **kwargs,
    )
