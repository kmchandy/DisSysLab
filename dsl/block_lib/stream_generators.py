"""
This file contains classes that generate streams of messages.
The base class is StreamGenerator. The file contains classes including
GenerateNumberSequence
GenerateRandomIntegers
GenerateFromList
GenerateFromFile
"""

from dsl.core import Agent

import requests
import time
import inspect
import types
from typing import Optional, Union, Callable, Any
from bs4 import BeautifulSoup

# =================================================
#          StreamGenerator                        |
# =================================================


class StreamGenerator(Agent):
    """
Name: StreamGenerator

Summary:
A StreamGenerator is a block that emits values from a Python generator function.

Parameters:
- name: Optional name for the block.
- description: Optional description.
- generator_fn (Callable[..., Generator]): 
        A generator function that yields values one at a time.
- args: Positional arguments to pass to generator_fn.
- kwargs: Keyword arguments to pass to generator_fn.
- delay: Optional delay (in seconds) between each output.

Behavior:
- A StreamGenerator is a block with no inports and one outport called "out".
- The block emits the values produced by generator_fn.
- If a delay is specified, the block waits for delay seconds between successive outputs.
- When generator_fn is exhausted, the block sends the special message "__STOP__" on its outport and halts.

Use Cases:
- Emit a sequence of numbers, events, or data rows
- Simulate time-series data or sensor output
- Drive downstream agents in a message-passing network

Example:
>>> def count_up_to(n):
>>>     for i in range(n):
>>>         yield i

>>> net = Network(
>>>     blocks={
>>>         'gen': StreamGenerator(generator_fn=count_up_to, kwargs={'n': 3}),
>>>         'receiver': StreamToList(),
>>>     },
>>>     connections=[('gen', 'out', 'receiver', 'in')]
>>> )
>>> net.compile()
>>> net.run()
>>> assert net.blocks['receiver'].saved == [0, 1, 2]

tags: source, generator, stream, delay, time-series, data rows
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
            raise TypeError(
                f"{generator_fn.__name__} did not return a generator. "
                f"Expected a generator, but got {type(gen).__name__}. "
                f"Did you forget to use 'yield' in your function?"
            )
        if kwargs is None:
            kwargs = {}

        def stream_fn(agent):
            gen = generator_fn(*args, **kwargs)
            if not inspect.isgenerator(gen):
                raise TypeError(
                    f"Expected generator, got {type(gen).__name__}")
            while True:
                try:
                    value = next(gen)
                    agent.send(value, "out")
                    if delay:
                        time.sleep(delay)
                except StopIteration:
                    agent.send("__STOP__", "out")
                    break
                except Exception as e:
                    print(f"❌ StreamGenerator error: {e}")
                    break

        super().__init__(
            name=name or "StreamGenerator",
            description=description or "Emits values from a generator function",
            inports=[],
            outports=["out"],
            run=stream_fn,
        )


# =================================================
#          generate                        |
# =================================================

def generate(source=None, delay=None, name=None):
    """
    Create a generator block from a list, generator function, or callable that returns a list or generator.

    Parameters:
    - source: A list, generator function, or callable returning a list or generator
    - delay: Optional delay between messages
    - name: Optional name for the block
    """
    if name is None:
        kind = (
            "list" if isinstance(source, list) else
            "callable" if callable(source) else
            "unknown"
        )
        name = f"generate_from_{kind}"

    if isinstance(source, list):
        return GenerateFromList(items=source, name=name, delay=delay)

    if callable(source):
        try:
            result = source()
            if isinstance(result, types.GeneratorType):
                return StreamGenerator(name=name, generator_fn=source, delay=delay)
            elif isinstance(result, list):
                return GenerateFromList(items=result, name=name, delay=delay)
            else:
                raise TypeError(
                    f"Callable must return a list or generator, got {type(result)}")
        except Exception as e:
            raise ValueError(
                f"Could not evaluate callable source for '{name}': {e}")

    raise TypeError(
        f"Unsupported source type: {type(source).__name__}. "
        f"'generate(...)' accepts a list, a generator function, or a callable returning one."
    )


# =================================================
#          GenerateFromList                        |
# =================================================
class GenerateFromList(StreamGenerator):
    """
Name: GenerateFromList

Summary:
A block that emits values from a predefined list.

Parameters:
- name: Optional name for the block.
- description: Optional description.
- items: List of values to emit.
- delay: Optional delay (in seconds) between outputs.

Behavior:
- Emits the items one at a time on its "out" port.
- Sends "__STOP__" after emitting the last item.

Use Cases:
- Provide a fixed set of prompts or commands
- Simulate user input or scripted sequences
- Control test cases or training data in pipelines

Example:
>>> net = Network(
        name="net",
>>>     blocks={
>>>         'gen': GenerateFromList(items=[
>>>             "What is the capital of France?",
>>>             "What did Joan of Arc do?"
>>>         ]),
>>>         'receiver': StreamToList(),
>>>     },
>>>     connections=[('gen', 'out', 'receiver', 'in')]
>>> )
>>> net.compile()
>>> net.run()
>>> assert len(net.blocks['receiver'].saved) == 2

tags: source, list, stream, prompts, scripted, test input
    """

    @staticmethod
    def _from_list(items):
        for item in items:
            yield item

    def __init__(
        self,
        items: list,
        delay: Optional[Union[int, float]] = None,
        name: Optional[str] = None,
        description: Optional[str] = None,
    ):
        super().__init__(
            name=name or "GenerateFromList",
            description=description or "Emits values from a predefined list",
            generator_fn=self._from_list,
            kwargs={"items": items},
            delay=delay,
        )


# =================================================
#         GenerateFromFile                        |
# =================================================
class GenerateFromFile(StreamGenerator):
    """
Name: GenerateFromFile

Summary:
A block that emits lines from a text file, one per output message.

Parameters:
- name: Optional name for the block.
- description: Optional description.
- filename: Path to the text file.
- delay: Optional delay (in seconds) between outputs.

Behavior:
- Emits one line at a time from the specified file.
- Strips whitespace from each line.
- Skips blank lines.
- Sends "__STOP__" after the file is fully read.

Use Cases:
- Stream log files or CSV rows
- Replay recorded sensor data or transcripts
- Drive simulations from text-based input

Example:
>>> with tempfile.NamedTemporaryFile(mode='w+', delete=False) as tmp:
>>>     tmp.write("apple\nbanana\ncarrot\n")
>>>     tmp_path = tmp.name

>>> net = Network(
>>>     blocks={
>>>         'gen': GenerateFromFile(filename=tmp_path),
>>>         'receiver': StreamToList(),
>>>     },
>>>     connections=[('gen', 'out', 'receiver', 'in')]
>>> )
>>> net.compile()
>>> net.run()
>>> assert net.blocks['receiver'].saved == ['apple', 'banana', 'carrot']

tags: source, file, text, replay, scripting, streaming
    """

    @staticmethod
    def _lines_from_file(filename):
        with open(filename) as f:
            for line in f:
                stripped = line.strip()
                if stripped:
                    yield stripped

    def __init__(
        self,
        filename: str,
        delay: Optional[Union[int, float]] = None,
        name: Optional[str] = None,
        description: Optional[str] = None,
    ):
        super().__init__(
            name=name or "GenerateFromFile",
            description=description or "Streams lines from a file",
            generator_fn=self._lines_from_file,
            kwargs={"filename": filename},
            delay=delay,
        )

# =================================================
#          GenerateTextFromURL                    |
# =================================================


class GenerateTextFromURL(StreamGenerator):
    """
Name: GenerateTextFromURL

Summary:
A block that streams clean text content from a public URL, split by paragraph or sentence.

Parameters:
- url: The URL of a webpage with visible, public text.
- split: Either "paragraph" or "sentence". Default: "paragraph".
- delay: Optional delay (in seconds) between emissions.
- name: Optional name of the block.
- description: Optional description.

Behavior:
- Fetches content from a URL.
- Parses visible text using BeautifulSoup.
- Splits content into paragraphs or sentences.
- Emits each chunk via the "out" port.
- Sends "__STOP__" after streaming all content.

Use Cases:
- Drive sentiment or entity extraction pipelines from live content.
- Analyze news, Wikipedia, or literature dynamically.
- Create educational pipelines with plug-and-play input from real-world sources.

Example:
>>> net = Network(
        name="net",
>>>     blocks={
>>>         'source': GenerateTextFromURL(
>>>             url="https://en.wikipedia.org/wiki/Artificial_intelligence",
>>>             split="paragraph"
>>>         ),
>>>         'analyze': SentimentClassifierWithGPT(),
>>>         'store': StreamToList(),
>>>     },
>>>     connections=[
>>>         ('source', 'out', 'analyze', 'in'),
>>>         ('analyze', 'out', 'store', 'in'),
>>>     ]
>>> )
>>> net.run()
>>> print(net.blocks['store'].saved)

tags: url, web scraping, source, wikipedia, article, text stream
    """

    @staticmethod
    def _fetch_text_from_url(url: str, split: str = "paragraph"):
        try:
            response = requests.get(url)
            # fallback is 'html.parser'
            soup = BeautifulSoup(response.text, 'lxml')
            paragraphs = soup.find_all('p')
            visible_text = "\n".join(p.get_text().strip()
                                     for p in paragraphs if p.get_text().strip())

            if split == "sentence":
                import re
                return (s.strip() for s in re.split(r'(?<=[.!?]) +', visible_text) if s.strip())
            else:
                return (p.strip() for p in visible_text.split('\n') if p.strip())
        except Exception as e:
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
            description=description or f"Stream visible text from URL {url}",
            generator_fn=self._fetch_text_from_url,
            kwargs={"url": url, "split": split},
            delay=delay,
        )
