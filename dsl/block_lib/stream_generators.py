
"""
stream_generators.py

This module defines generator blocks for emitting messages into a distributed network.
The core class is StreamGenerator. It also includes the `generate(...)` helper function
for creating generator blocks from lists or callables, and a web-based generator.

Classes:
- StreamGenerator
- GenerateTextFromURL

Functions:
- generate(source, delay=None, name=None)

tags: source, stream, generator, data, text, time-series
"""

import time
import types
import inspect
import requests
from bs4 import BeautifulSoup
from typing import Optional, Union, Callable, Any
from dsl.core import Agent

# =================================================
#                StreamGenerator                   |
# =================================================


class StreamGenerator(Agent):
    """
    A block that emits values from a generator function.

    Parameters:
    - name: Optional block name.
    - description: Optional description.
    - generator_fn: A Python generator function.
    - args: Optional positional arguments for generator_fn.
    - kwargs: Optional keyword arguments for generator_fn.
    - delay: Optional time delay (in seconds) between outputs.

    Behavior:
    - Emits values from the generator function on the 'out' port.
    - Sends a '__STOP__' message after generator completion.
    - Supports optional throttling via `delay`.

    Example:
    >>> def count_up_to(n): yield from range(n)
    >>> block = StreamGenerator(generator_fn=count_up_to, kwargs={'n': 3})
    """

    def __init__(
        self,
        name: Optional[str] = None,
        description: Optional[str] = None,
        generator_fn: Optional[Callable[..., Any]] = None,
        args: Optional[tuple] = (),
        kwargs: Optional[dict] = None,
        delay: Optional[Union[int, float]] = None
    ):
        if generator_fn is None:
            raise ValueError("StreamGenerator requires a generator_fn")
        if not callable(generator_fn):
            raise TypeError(f"{generator_fn} is not callable")
        if kwargs is None:
            kwargs = {}

        def stream_fn(agent):
            try:
                gen = generator_fn(*args, **kwargs)
                if not inspect.isgenerator(gen):
                    raise TypeError(
                        f"{generator_fn.__name__} did not return a generator. "
                        f"Expected a generator, but got {type(gen).__name__}. "
                        f"Did you forget to use 'yield'?"
                    )
                for value in gen:
                    agent.send(value, "out")
                    if delay:
                        time.sleep(delay)
                agent.send("__STOP__", "out")
            except Exception as e:
                print(f"❌ StreamGenerator error: {e}")
                agent.send("__STOP__", "out")

        super().__init__(
            name=name or "StreamGenerator",
            description=description or "Emits values from a generator function",
            inports=[],
            outports=["out"],
            run=stream_fn,
        )

# =================================================
#                    generate                      |
# =================================================


def generate(source=None, delay=None, name=None):
    """
    Create a StreamGenerator block from a list or generator function.

    Parameters:
    - source: A list, generator function, or callable returning a list or generator.
    - delay: Optional delay between outputs.
    - name: Optional name for the block.

    Returns:
    - A StreamGenerator instance.

    Example:
    >>> generate([1, 2, 3])
    >>> generate(lambda: (i for i in range(5)))
    """

    if name is None:
        kind = (
            "list" if isinstance(source, list) else
            "callable" if callable(source) else
            "unknown"
        )
        name = f"generate_from_{kind}"

    if isinstance(source, list):
        def list_generator():
            yield from source
        return StreamGenerator(
            name=name,
            generator_fn=list_generator,
            delay=delay
        )

    if callable(source):
        try:
            result = source()
            if isinstance(result, types.GeneratorType):
                return StreamGenerator(name=name, generator_fn=source, delay=delay)
            elif isinstance(result, list):
                def list_gen(): yield from result
                return StreamGenerator(name=name, generator_fn=list_gen, delay=delay)
            else:
                raise TypeError(
                    f"Callable must return a list or generator, got {type(result)}"
                )
        except Exception as e:
            raise ValueError(
                f"Could not evaluate callable source for '{name}': {e}")

    raise TypeError(
        f"Unsupported source type: {type(source).__name__}. "
        f"'generate(...)' accepts a list, a generator function, or a callable returning one."
    )

# =================================================
#              GenerateTextFromURL                 |
# =================================================


class GenerateTextFromURL(StreamGenerator):
    """
    A block that streams text content from a webpage.

    Parameters:
    - url: A publicly readable URL.
    - split: Either 'paragraph' or 'sentence'.
    - delay: Optional time delay between emissions.
    - name: Optional block name.
    - description: Optional description.

    Behavior:
    - Fetches visible text via requests + BeautifulSoup.
    - Splits content and emits chunks.
    - Sends '__STOP__' after streaming is complete.

    Example:
    >>> block = GenerateTextFromURL("https://en.wikipedia.org/wiki/AI", split="paragraph")
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
            print(f"⚠️ Error fetching {url}: {e}")
            yield f"[ERROR fetching URL: {e}]"

    def __init__(
        self,
        url: str,
        split: str = "paragraph",
        delay: Optional[Union[int, float]] = None,
        name: Optional[str] = None,
        description: Optional[str] = None,
    ):
        super().__init__(
            name=name or "GenerateTextFromURL",
            description=description or f"Streams text from URL: {url}",
            generator_fn=self._fetch_text_from_url,
            kwargs={"url": url, "split": split},
            delay=delay,
        )
