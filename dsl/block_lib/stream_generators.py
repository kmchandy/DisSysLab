"""
This file contains classes that generate streams of messages.
The base class is StreamGenerator. The file contains classes including
GenerateNumberSequence
GenerateRandomIntegers
GenerateFromList
GenerateFromFile
"""

from dsl.core import Network
from dsl.block_lib.stream_recorders import StreamToList

import requests
from typing import Optional, Union
from bs4 import BeautifulSoup
from typing import Optional, Union, Callable, Any
import time
import inspect
import random
from dsl.core import Agent

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
        if not inspect.isgeneratorfunction(generator_fn):
            raise TypeError(
                f"Expected a generator function, got {type(generator_fn).__name__}")
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
#        GenerateNumberSequence                   |
# =================================================
class GenerateNumberSequence(StreamGenerator):
    """
Name: GenerateNumberSequence

Summary:
GenerateNumberSequence emits values in a range from low to high with the specified step_size

Parameters:
- name: Optional name for the block.
- description: Optional description.
- low: int or float. Low end of the range of values.
- high: int or float. High end of the range of values.
- step_size: int or float. Step size in generating the range of values.
- delay: Optional delay (in seconds) between each output.

Behavior:
- A GenerateNumberSequence is a block with no inports and one outport called "out".
- The block sends values from low to high with the specifed step size on port "out"
- If a delay is specified, the block waits for delay seconds between successive outputs.
- After sending all values in the range the block the block sends the special message 
  "__STOP__" on its outport and halts.

Use Cases:
- Emit a sequence of numbers
- Simulate time-series data or sensor output
- Drive downstream agents in a message-passing network

Example:
>>> net = Network(
>>>     blocks={
>>>         'gen': GenerateNumberSequence(low=0, high=3, step_size=1),
>>>         'receiver': StreamToList(),
>>>     },
>>>     connections=[('gen', 'out', 'receiver', 'in')]
>>> )
>>> net.run()
>>> assert net.blocks['receiver'].saved == [0, 1, 2]

tags: source, generator, stream, delay, range, time-series
    """
    @staticmethod
    def _count_by_step(low: int, high: int, step_size: int):
        if step_size == 0:
            raise ValueError("step_size must not be zero")

        if (step_size > 0 and low >= high) or (step_size < 0 and low <= high):
            return  # nothing to yield

        current = low
        while (step_size > 0 and current < high) or (step_size < 0 and current > high):
            yield current
            current += step_size

    def __init__(
        self,
        low: Union[int, float],
        high: Union[int, float],
        step_size: Union[int, float],
        delay: Optional[Union[int, float]] = None,
        name: Optional[str] = None,
        description: Optional[str] = None,
    ):
        super().__init__(
            name=name or "GenerateNumberSequence",
            description=description or "Generates numbers from low to high in step_size",
            generator_fn=self._count_by_step,  # ✅ staticmethod is callable from instance
            kwargs={"low": low, "high": high, "step_size": step_size},
            delay=delay,
        )


# =================================================
#      GenerateRandomIntegers                     |
# =================================================
class GenerateRandomIntegers(StreamGenerator):
    """
Name: GenerateRandomIntegers

Summary:
A block that emits a sequence of random integers in the range [lo, hi].

Parameters:
- name: Optional name for the block.
- description: Optional description.
- count: Number of random integers to generate.
- lo: Lower bound (inclusive).
- hi: Upper bound (inclusive).
- delay: Optional delay (in seconds) between outputs.

Behavior:
- Emits `count` random integers in the range [lo, hi].
- Sends each value on its "out" port.
- After emitting all values, sends "__STOP__" and halts.

Use Cases:
- Simulate random event streams
- Generate synthetic input for downstream blocks
- Demonstrate randomness in distributed systems

Example:
>>> net = Network(
>>>     blocks={
>>>         'gen': GenerateRandomIntegers(count=5, lo=10, hi=20),
>>>         'receiver': StreamToList(),
>>>     },
>>>     connections=[('gen', 'out', 'receiver', 'in')]
>>> )
>>> net.run()
>>> assert len(net.blocks['receiver'].saved) == 5

tags: source, generator, stream, random, testing, synthetic data
    """

    @staticmethod
    def _random_integers(count: int, lo: int, hi: int):
        for _ in range(count):
            yield random.randint(lo, hi)

    def __init__(
        self,
        count: int,
        lo: int,
        hi: int,
        delay: Optional[Union[int, float]] = None,
        name: Optional[str] = None,
        description: Optional[str] = None,
    ):
        if lo >= hi:
            raise ValueError(
                f"In generate random integers, low >= hi. lo = {lo}, hi = {hi}")
        if count < 0:
            raise ValueError(
                f"In generate random integers, count is negative. count = {count}")

        super().__init__(
            name=name or "GenerateRandomIntegers",
            description=description or "Generates random integers in a range",
            generator_fn=self._random_integers,
            kwargs={"count": count, "lo": lo, "hi": hi},
            delay=delay,
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
