"""
Module: stream_transformers.py

Summary:
Defines the StreamTransformer class and several classes that inherit from it.
These classes help in creating blocks that receive messages on the block's
only inport and output messages on the block's only outport. The block's 
inport and outport are called 'in' and 'out', respectively. A StreamTransformer
receives a message from its "in" port, applies a transformation
function to the message, and emits the result on its "out" port.

The classes in this module include:
1. StreamTransformer
2. WrapFunction
3. TransformMultipleStreams
4. SentimentClassifierWithGPT
5. ExtractEntitiesWithGPT
6. SummarizeWithGPT


tags: transformer, stream, block, natural language, numeric, processing
"""

from stream_generators import GenerateNumberSequence
from typing import Optional
from dsl.core import Network, StreamToList
from dotenv import load_dotenv
import os
from openai import OpenAI
from typing import Optional, Union, Callable, Any
import inspect
import time
from dsl.core import Agent, Network, StreamToList
from dsl.stream_generators import GenerateFromList

# =================================================
#   StreamTransformer                            |
# =================================================


class StreamTransformer(Agent):
    """
Name: StreamTransformer

Summary:
A StreamTransformer applies a function to each incoming message and emits the result.

Parameters:
- name: Optional name for the block.
- description: Optional description.
- transform_fn: A callable that takes one input value and returns one output.
- args: Optional positional arguments passed to transform_fn.
- kwargs: Optional keyword arguments passed to transform_fn.
- delay: Optional delay (in seconds) between receiving and sending messages.

Behavior:
- Receives input on "in", applies transform_fn to each message.
- Emits the result on "out".
- When "__STOP__" is received, it forwards "__STOP__" and halts.

Use Cases:
- Numeric or text transformations
- Natural language interpretation


tags: transformer, stream, processing, function, delay
    """

    def __init__(
        self,
        transform_fn: Callable[..., Any],
        args: Optional[tuple] = (),
        kwargs: Optional[dict] = None,
        delay: Optional[Union[int, float]] = None,
        name: Optional[str] = None,
        description: Optional[str] = None,
    ):
        if not callable(transform_fn):
            raise TypeError("transform_fn must be callable")
        if kwargs is None:
            kwargs = {}

        def run_fn(agent):
            while True:
                msg = agent.recv("in")
                if msg == "__STOP__":
                    agent.send("__STOP__", "out")
                    break
                try:
                    result = transform_fn(msg, *args, **kwargs)
                    agent.send(result, "out")
                    if delay:
                        time.sleep(delay)
                except Exception as e:
                    print(f"❌ StreamTransformer error: {e}")
                    agent.send("__STOP__", "out")
                    break

        super().__init__(
            name=name or "StreamTransformer",
            description=description or "Output message is function of input message",
            inports=["in"],
            outports=["out"],
            run_fn=run_fn,
        )


# =================================================
#   WrapFunction                           |
# =================================================
class WrapFunction(Agent):
    """
    Name: WrapFunction

    Summary:
    WrapFunction encapsulates a function in a library, such as NumPy, into a block.

    Parameters:
    - name: Optional name for the block.
    - description: Optional description. If not provided, the function docstring is used.
    - function: A callable function to be wrapped.
    - args: Positional arguments to be passed to the function (after the stream input).
    - kwargs: Keyword arguments to be passed to the function.

    Behavior:
    - Receives one input on port "in".
    - Applies the wrapped function to the input, optionally using args and kwargs.
    - Emits the result on port "out".
    - Forwards "__STOP__" if received.

    Use Cases:
    - Easily integrate existing numerical or AI functions into a streaming pipeline
    - Convert any single-input Python function into a reusable block
    - Rapidly prototype complex networks using external libraries

    Example:
    >>> import numpy as np
    >>> from dsl.core import Network, StreamToList, GenerateFromList
    >>> net = Network(
    >>>     blocks={
    >>>         'input': GenerateFromList(items=[[1, 2], [3, 4]]),
    >>>         'inverse': WrapFunction(np.linalg.inv),
    >>>         'output': StreamToList(),
    >>>     },
    >>>     connections=[('input', 'out', 'inverse', 'in'),
    >>>                  ('inverse', 'out', 'output', 'in')]
    >>> )
    >>> net.run()
    >>> print(net.blocks['output'].saved)

    tags: wrap, function, transform, library, numpy, plug-and-play, streaming
    """

    def __init__(
        self,
        function: Callable[..., Any],
        name: Optional[str] = None,
        description: Optional[str] = None,
        args: Optional[tuple] = (),
        kwargs: Optional[dict] = None,
    ):
        if not callable(function):
            raise TypeError("function must be callable")

        self.function = function
        self.args = args or ()
        self.kwargs = kwargs or {}

        # Check compatibility with inspect.signature
        try:
            sig = inspect.signature(function)
            sig.bind_partial(None, *self.args, **self.kwargs)
        except Exception as e:
            raise ValueError(
                f"Invalid args/kwargs for function {function.__name__}: {e}")

        # Generate description from function docstring if not provided
        doc_line = (function.__doc__ or '').strip().split('\n')[0]
        full_description = description or f"Applies {function.__name__} — {doc_line}"

        def transform_fn(value):
            return self.function(value, *self.args, **self.kwargs)

        def run_fn(agent):
            while True:
                msg = agent.recv("in")
                if msg == "__STOP__":
                    agent.send("__STOP__", "out")
                    break
                try:
                    result = transform_fn(msg)
                    agent.send(result, "out")
                except Exception as e:
                    print(f"❌ Error in {function.__name__}: {e}")

        super().__init__(
            name=name or function.__name__,
            description=full_description,
            inports=["in"],
            outports=["out"],
            run_fn=run_fn,
        )


# =================================================
#   TransformMultipleStreams                      |
# =================================================
class TransformMultipleStreams(Agent):
    """
    Name: TransformMultipleStreams

    Summary:
    A block that merges messages from multiple input ports into a list.
    If a transformer function is provided, it applies the function to the list;
    otherwise, it simply forwards the merged list to the output.


    Parameters:
    - name: Optional name for the block.
    - inports: Non-empty list of names of inports.
    - transformer_fn: A callable that executes on a tuple with one
              value from each inport.

    Behavior:
    - Waits until one message is available on each input port.
    - Applies the transformation function to the merged input - a list.
    - Sends the result to the "out" port.
    - Sends "__STOP__" if the block receives "__STOP__" from any inport.

    Use Cases:
    - Join and transform parallel stream outputs
    - Combine results such as sentiment, entity, clarity of text into a structured object

    Example:
    >>> def combine(sentiment_entities_tuple):
    >>>     return {"sentiment": sentiment_entities_tuple[0], 
    >>>             "entities": sentiment_entities_tuple[1]}

    >>> class MergeSentimentAndEntities(TransformMultipleStreams):
    >>>     def __init__():
    >>>         super().__init__(name="Merge", inports=["sentiment", "entities"], transformer_fn=combine)

    tags: merge, transform, join, combine, multi-input
    """
    """
    Name: TransformMultipleStreams

    Summary:
    A block that merges messages from multiple input ports into a
    list and optionally applies a function to the list. The result
    is sent to the block's only output port 'out'.

    Parameters:
    - name: Optional name for the block.
    - inports: Non-empty list of names of inports.
    - transformer_fn: A callable that executes on a list of one
      message from each inport. If not provided, the merged list
      is sent as-is.

    Behavior:
    - Waits until one message is available on each input port.
    - Merges one message from each input into a list.
    - Applies the transformation function to the list (if provided).
    - Sends the result on the "out" port.
    - Sends "__STOP__" if the block receives "__STOP__" from any inport.

    Use Cases:
    - Join and transform parallel stream outputs
    - Combine results such as sentiment, entities, and clarity into a structured object
    - Merge multiple sequences or signals for comparison or analysis

    Example (no transform_fn — just merging into a list):
    >>> net = Network(
    >>>     blocks={
    >>>         'seq_0': GenerateNumberSequence(low=0, high=3, step_size=1),
    >>>         'seq_1': GenerateNumberSequence(low=3, high=6, step_size=1),
    >>>         'merge': TransformMultipleStreams(inports=['in_0', 'in_1']),
    >>>         'result': StreamToList(),
    >>>     },
    >>>     connections=[
    >>>         ('seq_0', 'out', 'merge', 'in_0'),
    >>>         ('seq_1', 'out', 'merge', 'in_1'),
    >>>         ('merge', 'out', 'result', 'in'),
    >>>     ]
    >>> )
    >>> net.run()
    >>> assert net.blocks['result'].saved == [[0, 3], [1, 4], [2, 5]]
    Example:
    >>> def combine(sentiment_entities_tuple):
    >>>     return {"sentiment": sentiment_entities_tuple[0], 
    >>>             "entities": sentiment_entities_tuple[1]}

    >>> class MergeSentimentAndEntities(TransformMultipleStreams):
    >>>     def __init__():
    >>>         super().__init__(name="Merge", inports=["sentiment", "entities"], transformer_fn=combine)

    Note:
    - When no transformer function is provided, the output will be a list
      containing one item from each input port, in port order.
    - For structured output (e.g., dict), use a transformer_fn or subclass.

    tags: merge, transform, join, combine, multi-input, buffer, parallel
    """

    def __init__(
        self,
        name: Optional[str] = None,
        inports: Optional[list[str]] = None,
        transformer_fn: Optional[Callable[..., Any]] = None
    ):
        if inports is None:
            raise ValueError(
                "TransformMultipleStreams requires inports to be specified")

        super().__init__(
            name=name or "TransformMultipleStreams",
            inports=inports,
            outports=["out"]
        )
        self.transformer_fn = transformer_fn
        self.buffers = {port: [] for port in self.inports}

    def run(self):
        while True:
            for inport in self.inports:
                msg = self.recv(inport)
                if msg == "__STOP__":
                    self.send("__STOP__", "out")
                    return
                self.buffers[inport].append(msg)

            if all(self.buffers[port] for port in self.inports):
                args = [self.buffers[port].pop(0) for port in self.inports]
                try:
                    result = self.transformer_fn(
                        args) if self.transformer_fn else args
                    self.send(result, "out")
                except Exception as e:
                    print(f"❌ TransformMultipleStreams error: {e}")
                    continue


net = Network(
    blocks={
        'seq_0': GenerateNumberSequence(low=0, high=3, step_size=1),
        'seq_1': GenerateNumberSequence(low=3, high=6, step_size=1),
        'merge': TransformMultipleStreams(inports=['in_0', 'in_1']),
        'result': StreamToList(),
    },
    connections=[
        ('seq_0', 'out', 'merge', 'in_0'),
        ('seq_1', 'out', 'merge', 'in_1'),
        ('merge', 'out', 'result', 'in'),
    ]
)
net.run()
assert (net.blocks['result'].saved == [[0, 3], [1, 4], [2, 5]])


# =================================================
#  FOR GPT APPLICATIONS: CREATE CLIENT            |
# =================================================
# Load API key from .env file
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)

# =================================================
#        SentimentClassifierWithGPT              |
# =================================================


class SentimentClassifierWithGPT(StreamTransformer):
    """
Name: SentimentClassifierWithGPT

Summary:
Classifies the sentiment of each message using OpenAI's GPT model.

Parameters:
- model: Name of the OpenAI model to use (default "gpt-3.5-turbo").
- delay: Optional delay between processing steps.

Behavior:
- Sends each message to OpenAI with a prompt asking for "positive", "negative", or "neutral" classification.
- Emits the result on the outport.

Use Cases:
- Realistic sentiment classification
- Teach integration of AI models in message-passing systems
- Analyze student feedback, product reviews, etc.

Example:
>>> net = Network(
>>>     blocks={
>>>         'generate sentences': GenerateFromList(items=[
>>>             "I really love this course!",
>>>             "This is terrible.",
>>>             "'Mona Lisa' is a beautiful painting",
>>>             "I don't have an opinion."
>>>         ]),
>>>         'classify sentence sentiment': SentimentClassifierWithGPT(),
>>>         'record sentence sentiment': StreamToList(),
>>>     },
>>>     connections=[
>>>         ('generate sentences', 'out', 'classify sentence sentiment', 'in'),
>>>         ('classify sentence sentiment', 'out', 'record sentence sentiment', 'in'),
>>>     ],
>>> )
>>> net.run()
>>> print(f"Sentiments are {net.blocks['record sentence sentiment'].saved}")
>>> Expected output: 'positive', 'negative', 'positive', 'neutral'

tags: transformer, NLP, sentiment, OpenAI, GPT, classification
    """

    @staticmethod
    def _classify_gpt(msg: str, model: str) -> str:
        prompt = f"""
You are a helpful assistant that classifies sentiment.
Classify the following text as Positive, Negative, or Neutral.

Text: "{msg}"
Sentiment:
"""
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"error: {e}"

    def __init__(self, model: str = "gpt-3.5-turbo", delay: Optional[float] = None):
        super().__init__(
            transform_fn=self._classify_gpt,
            kwargs={"model": model},
            delay=delay,
            name="SentimentClassifierWithGPT"
        )


net = Network(
    blocks={
        'generate sentences': GenerateFromList(items=[
            "I really love this course!",
            "This is terrible.",
            "'My Fair Lady' is a beautiful musical",
            "I don't have an opinion."
        ]),
        'classify sentence sentiment': SentimentClassifierWithGPT(),
        'record sentence sentiment': StreamToList(),
    },
    connections=[
        ('generate sentences', 'out', 'classify sentence sentiment', 'in'),
        ('classify sentence sentiment', 'out', 'record sentence sentiment', 'in'),
    ],
)
net.run()
print(f'Sentiments are {net.blocks['record sentence sentiment'].saved}')


# =================================================
#          ExtractEntitiesWithGPT                |
# =================================================
class ExtractEntitiesWithGPT(Agent):
    """
Name: ExtractEntitiesWithGPT

Summary:
Uses OpenAI's GPT model to extract named entities from input text.

Parameters:
- name: Optional name for the block.
- model: Optional model name (default is "gpt-3.5-turbo").
- delay: Optional delay (in seconds) between API calls.

Behavior:
- Accepts a sentence on input port "in".
- Sends a list of named entities (strings) on port "out".
- Uses a structured prompt to ask GPT for entity extraction.

Use Cases:
- Extract names of people, organizations, locations from a sentence
- Use as a component in text understanding or knowledge graph generation
- Parallel processing with sentiment classifiers or summarizers

Example:
>>> net = Network(
>>>     blocks={
>>>         'generate': GenerateFromList(items=[
>>>             "OpenAI and Meta are transforming AI.",
>>>             "Elon Musk leads Tesla and SpaceX."
>>>         ]),
>>>         'entities': ExtractEntitiesWithGPT(),
>>>         'collector': StreamToList(),
>>>     },
>>>     connections=[
>>>         ('generate', 'out', 'entities', 'in'),
>>>         ('entities', 'out', 'collector', 'in'),
>>>     ]
>>> )
>>> net.run()
>>> print(net.blocks['collector'].saved)

Expected Output:
[['OpenAI', 'Meta'], ['Elon Musk', 'Tesla', 'SpaceX']]

tags: gpt, entity extraction, named entities, NLP, OpenAI, language model
    """

    def __init__(
        self,
        name: Optional[str] = None,
        model: str = "gpt-3.5-turbo",
        delay: Optional[Union[int, float]] = None
    ):
        super().__init__(
            name=name or "ExtractEntitiesWithGPT",
            inports=["in"],
            outports=["out"]
        )
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = model
        self.delay = delay

    def run(self):
        while True:
            msg = self.recv("in")
            if msg == "__STOP__":
                self.send("__STOP__", "out")
                return

            prompt = f"""
You are an information extraction assistant.
Extract all named entities (people, places, organizations, etc.) from the following sentence.
Respond ONLY with a Python list of strings:

Text: "{msg}"
            """

            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}]
                )
                entities_text = response.choices[0].message.content.strip()
                entities = eval(
                    entities_text) if entities_text.startswith("[") else []
                self.send(entities, "out")

                if self.delay:
                    time.sleep(self.delay)
            except Exception as e:
                print(f"❌ ExtractEntitiesWithGPT error: {e}")
                self.send([], "out")


# =================================================
#              SummarizeWithGPT                  |
# =================================================
class SummarizeWithGPT(StreamTransformer):
    """
    Name: SummarizeWithGPT

    Summary:
    A transformer block that summarizes each incoming message using OpenAI's GPT.

    Parameters:
    - name: Optional name for the block.
    - model: GPT model name to use (e.g., "gpt-3.5-turbo").
    - max_words: Optional upper bound on summary length in words.
    - temperature: Sampling temperature for GPT output.

    Behavior:
    - Receives a long paragraph or sentence on port "in".
    - Sends back a concise summary on port "out".
    - Handles errors gracefully and returns a fallback string on failure.

    Use Cases:
    - Summarize emails, articles, or logs
    - Compress context for long conversations
    - Convert verbose user input to intent summary

    Example:
    >>> net = Network(
    >>>     blocks={
    >>>         'generate': GenerateFromList(items=[
    >>>             "The quick brown fox jumps over the lazy dog. It then runs into the forest and howls.",
    >>>             "OpenAI has released new capabilities in its API, including new models and tools."
    >>>         ]),
    >>>         'summarize': SummarizeWithGPT(),
    >>>         'collector': StreamToList(),
    >>>     },
    >>>     connections=[
    >>>         ('generate', 'out', 'summarize', 'in'),
    >>>         ('summarize', 'out', 'collector', 'in'),
    >>>     ]
    >>> )
    >>> net.run()
    >>> print(net.blocks['collector'].saved)

    tags: summarize, gpt, llm, transformer, compress, abstract, text
    """

    def __init__(
        self,
        name: Optional[str] = None,
        model: str = "gpt-3.5-turbo",
        max_words: Optional[int] = 50,
        temperature: float = 0.3
    ):
        super().__init__(
            name=name or "SummarizeWithGPT",
            description="Summarizes text using OpenAI's GPT",
            transform_fn=self.summarize,
        )
        load_dotenv()
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("Missing OPENAI_API_KEY in environment.")
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.max_words = max_words
        self.temperature = temperature

    def summarize(self, text: str) -> str:
        try:
            prompt = f"""
            Summarize the following in no more than {self.max_words} words:

            """
            prompt += text

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system",
                        "content": "You are a helpful assistant that summarizes text."},
                    {"role": "user", "content": prompt}
                ],
                temperature=self.temperature
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"error: {e}"
