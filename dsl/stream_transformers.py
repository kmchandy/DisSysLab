"""
Module: stream_transformers.py

Summary:
Defines the StreamTransformer class and several reusable transformer blocks
for modifying, interpreting, or extracting information from a stream of messages.

Each transformer receives messages from its "in" port, applies a transformation
function, and emits the result on its "out" port.

tags: transformer, stream, block, natural language, numeric, processing
"""

from dsl.core import Network, StreamToList
from dotenv import load_dotenv
import os
from openai import OpenAI
from typing import Optional, Union, Callable, Any
import inspect
import time
from dsl.core import Agent
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
