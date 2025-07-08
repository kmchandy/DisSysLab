"""
Module: stream_transformers.py

Summary:
Defines the StreamTransformer class and several reusable transformer blocks
for modifying, interpreting, or extracting information from a stream of messages.

Each transformer receives messages from its "in" port, applies a transformation
function, and emits the result on its "out" port.

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
- Preprocessing streams before agents

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
            description=description or "Transforms input stream with a function",
            inports=["in"],
            outports=["out"],
            run_fn=run_fn,
        )


load_dotenv()
client = OpenAI()


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


class TransformMultipleStreams(Agent):
    """
    TransformMultipleStreams

    Summary:
    A block that merges messages from multiple input ports and applies
    a transformation function before emitting a single output.

    Parameters:
    - name: Optional name for the block.
    - transformer_fn: A callable that receives one value from each input port
      and returns a transformed result.

    Behavior:
    - Waits until one message is available on each input port.
    - Applies the transformation function to the merged input.
    - Sends the result to the "out" port.
    - Sends "__STOP__" if any input receives "__STOP__".

    Use Cases:
    - Join and transform parallel stream outputs
    - Combine results such as sentiment, entity, clarity of text into a structured object
    - Aggregate or compute across input dimensions

    Example:
    >>> def combine(sentiment, entities):
    >>>     return {"sentiment": sentiment, "entities": entities}

    >>> class MergeSentimentAndEntities(TransformMultipleStreams):
    >>>     def __init__():
    >>>         super().__init__(name="Merge", inports=["sentiment", "entities"], transformer_fn=combine)

    tags: merge, transform, join, combine, multi-input
    """

    def __init__(
        self,
        name: Optional[str] = None,
        inports: Optional[list] = None,
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
print(f'result is {net.blocks['result'].saved} \n')


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
