
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
import traceback
from rich import print as rprint
from bs4 import BeautifulSoup
from typing import Optional, Union, Callable, Any
from dsl.core import Agent, SimpleAgent


# =================================================
#                StreamGenerator                   |
# =================================================


class StreamGenerator(Agent):
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

    def __init__(self, name=None, generator_fn=None, delay=None,  *args, **kwargs):
        if generator_fn is None:
            raise ValueError("StreamGenerator requires a generator_fn")

        def run_fn(agent):
            try:
                for msg in generator_fn(*args, **kwargs):
                    agent.send(msg, "out")
                    if delay:
                        import time
                        time.sleep(delay)
                agent.send("__STOP__", "out")

            except Exception as e:
                # Rich-formatted error
                rprint(f"[bold red]❌ StreamGenerator error:[/bold red] {e}")

                # Write full traceback to debug log
                with open("dsl_debug.log", "a") as log:
                    log.write("\n--- StreamGenerator Error ---\n")
                    log.write(traceback.format_exc())

                raise  # Re-raise to allow test or framework to detect failure

        super().__init__(
            name=name or "StreamGenerator",
            description="Generate stream from Python generator",
            inports=[],
            outports=["out"],
            run=run_fn
        )


# =================================================
#                    generate                      |
# =================================================


def generate(source=None, delay=None, name=None, *args, **kwargs):
    """
    Create a StreamGenerator block from a list, generator, or a function returning one.

    Parameters:
    - source: list | generator function | callable returning list/generator
    - delay: Optional delay between messages
    - name: Optional block name
    - *args, **kwargs: Passed to source if it’s a callable

    Returns:
    - StreamGenerator instance
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
        def wrapped_generator():
            result = source(*args, **kwargs)
            if isinstance(result, types.GeneratorType):
                yield from result
            elif isinstance(result, list):
                yield from result
            else:
                raise TypeError(
                    f"Callable must return a list or generator, got {type(result)}"
                )
        return StreamGenerator(name=name, generator_fn=wrapped_generator, delay=delay)
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
