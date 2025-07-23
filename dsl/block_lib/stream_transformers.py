"""
Module: stream_transformers.py

Summary:
Defines the StreamTransformer class and several variants for transforming data
streams. These include wrappers for arbitrary Python functions, multi-stream
transformations, and GPT-based transformations using OpenAI's API.

Each block receives messages on a single inport or multiple inports and emits
transformed output on an outport. These blocks are useful for teaching distributed
stream processing with natural language and numerical data.

Tags: transformer, stream, block, NLP, OpenAI, NumPy, GPT, data processing
"""

from typing import Optional, Callable, Any, Union
from dotenv import load_dotenv
from openai import OpenAI
import os
import ast
from dsl.core import SimpleAgent, Agent

# =================================================
#          StreamTransformer                      |
# =================================================


class StreamTransformer(SimpleAgent):
    """
    An instance of a StreamTransformer is an agent with a single inport called "in" and
    a single outport called "out". The agent receives a message along inport "in",
    applies function transform_fn to the message and sends the result on outport "out".
    transform_fn may have args and kwargs.

    Args:
        SimpleAgent (_type_): _description_
    """

    def __init__(
        self,
        transform_fn: Callable[..., Any],
        args: Optional[tuple] = (),
        kwargs: Optional[dict] = None,
        name: Optional[str] = None,
        description: Optional[str] = None,
    ):
        if not callable(transform_fn):
            raise TypeError(
                f"transform_fn must be callable, got {type(transform_fn)}")
        if kwargs is None:
            kwargs = {}

        def handle_msg(agent, msg):
            try:
                result = transform_fn(msg, *args, **kwargs)
                agent.send(result, "out")
            except Exception as e:
                print(
                    f"❌ StreamTransformer error: input={msg!r}, type={type(msg).__name__}, error={e}")
                agent.send("__STOP__", "out")

        super().__init__(
            name=name or "StreamTransformer",
            description=description or "Applies a function to each stream message",
            inport="in",
            outports=["out"],
            handle_msg=handle_msg,
        )


# =================================================
#              WrapFunction                       |
# =================================================

class WrapFunction(StreamTransformer):
    def __init__(
        self,
        func: Callable[[Any], Any],
        args: Optional[tuple] = (),
        kwargs: Optional[dict] = None,
        name: Optional[str] = None,
        description: Optional[str] = None,
    ):
        if not callable(func):
            raise TypeError(
                f"WrapFunction expects a callable, got {type(func)}")
        super().__init__(
            transform_fn=func,
            args=args,
            kwargs=kwargs,
            name=name or "WrapFunction",
            description=description or f"Wraps function: {func.__name__}",
        )


# =================================================
#         PromptToBlock (WrapPrompt)              |
# =================================================

class PromptToBlock(SimpleAgent):
    def __init__(
        self,
        prompt: str,
        model: str = "gpt-3.5-turbo",
        temperature: float = 0.7,
        name: Optional[str] = None,
        description: Optional[str] = None,
    ):
        if not prompt:
            raise ValueError("PromptToBlock requires a prompt.")

        load_dotenv()
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY is missing in environment.")

        client = OpenAI(api_key=api_key)

        def handle_msg(agent, msg):
            try:
                rendered_prompt = prompt.replace("{msg}", str(msg))
                response = client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": rendered_prompt}],
                    temperature=temperature
                )
                reply = response.choices[0].message.content.strip()
                agent.send(reply, "out")
            except Exception as e:
                print(f"❌ PromptToBlock error: {e}")
                agent.send("__STOP__", "out")

        super().__init__(
            name=name or "PromptToBlock",
            description=description or f"LLM prompt block: {prompt[:40]}...",
            inport="in",
            outports=["out"],
            handle_msg=handle_msg,
        )


# =================================================
#        SentimentClassifierWithGPT              |
# =================================================

class SentimentClassifierWithGPT(StreamTransformer):
    def __init__(self, model: str = "gpt-3.5-turbo"):
        load_dotenv()
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY is missing in environment.")
        self.client = OpenAI(api_key=api_key)
        self.model = model

        def classify(msg: str) -> str:
            prompt = f"""You are a helpful assistant. Classify the sentiment of the following text as Positive, Negative, or Neutral.\nText: \"{msg}\"\nSentiment:"""
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0
                )
                return response.choices[0].message.content.strip()
            except Exception as e:
                return f"error: {e}"

        super().__init__(transform_fn=classify, name="SentimentClassifierWithGPT")


# =================================================
#        ExtractEntitiesWithGPT                   |
# =================================================

class ExtractEntitiesWithGPT(StreamTransformer):
    def __init__(self, model: str = "gpt-3.5-turbo"):
        load_dotenv()
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY is missing in environment.")
        self.client = OpenAI(api_key=api_key)
        self.model = model

        def extract(msg: str) -> list[str]:
            prompt = f"""Extract all named entities from the text and return them as a Python list of strings.\nText: \"{msg}\" """
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                )
                text = response.choices[0].message.content.strip()
                return ast.literal_eval(text) if text.startswith("[") else []
            except Exception as e:
                print(f"❌ ExtractEntitiesWithGPT error: {e}")
                return []

        super().__init__(transform_fn=extract, name="ExtractEntitiesWithGPT")


# =================================================
#           SummarizeWithGPT                      |
# =================================================

class SummarizeWithGPT(StreamTransformer):
    def __init__(
        self,
        max_words: int = 50,
        temperature: float = 0.3,
        model: str = "gpt-3.5-turbo"
    ):
        load_dotenv()
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY is missing in environment.")
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.max_words = max_words
        self.temperature = temperature

        def summarize(text: str) -> str:
            prompt = f"Summarize the following in no more than {self.max_words} words:\n\n{text}"
            try:
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

        super().__init__(transform_fn=summarize, name="SummarizeWithGPT")


# =================================================
#        TransformMultipleStreams                 |
# =================================================

class TransformMultipleStreams(Agent):
    """
    An instance of TransformMultipleStreams is an agent that has 
    multiple inports and a single outport called "out". The
    agent waits to receive a message on each of its inports and 
    then applies the specified function, transformer_fn, to the 
    list of messages and outputs the result.

    Args:
        Agent (_type_): _description_
    """

    def __init__(
        self,
        inports: list[str],
        transformer_fn: Optional[Callable[[list[Any]], Any]] = None,
        name: Optional[str] = None
    ):
        if not inports:
            raise ValueError(
                "TransformMultipleStreams requires at least one inport.")
        super().__init__(name=name or "TransformMultipleStreams",
                         inports=inports, outports=["out"], run=self.run)
        self.transformer_fn = transformer_fn
        self.buffers = {port: [] for port in self.inports}

    def run(self):
        # If a "__STOP__" message is received on any inport the agent stops
        # after sending "__STOP__" on its outport. This run() must be
        # modified to fit other stopping conditions.
        while True:
            for port in self.inports:
                msg = self.recv(port)
                if msg == "__STOP__":
                    self.send("__STOP__", "out")
                    return
                self.buffers[port].append(msg)

            if all(self.buffers[port] for port in self.inports):
                inputs = [self.buffers[port].pop(0) for port in self.inports]
                try:
                    result = self.transformer_fn(
                        inputs) if self.transformer_fn else inputs
                    self.send(result, "out")
                except Exception as e:
                    print(f"❌ TransformMultipleStreams error: {e}")
                    self.send("__STOP__", "out")
