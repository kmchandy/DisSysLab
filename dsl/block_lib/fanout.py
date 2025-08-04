"""
Module: stream_transformers.py

Summary:
Defines the StreamTransformer class and several variants for transforming data
streams. These include wrappers for arbitrary Python functions, multi-stream
transformations, and GPT-based transformations using OpenAI's API.

Tags: ["transformer", "stream", "block", "NLP", "OpenAI", "NumPy", "GPT"]
"""

import os
import ast
import traceback
from typing import Optional, Callable, Any, Union
from dotenv import load_dotenv
from openai import OpenAI
from rich import print as rprint

from dsl.core import SimpleAgent, Agent

DEBUG_LOG = "dsl_debug.log"

# =================================================
#          StreamTransformer                      |
# =================================================


class StreamTransformer(SimpleAgent):
    """
    StreamTransformer applies a transformation function to each input message.

    - inport: "in"
    - outport: "out"
    - transform_fn(msg, *args, **kwargs) → result
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
                rprint(f"[bold red]❌ StreamTransformer error:[/bold red] {e}")
                with open(DEBUG_LOG, "a") as f:
                    f.write("\n--- StreamTransformer Error ---\n")
                    f.write(traceback.format_exc())
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
                rprint(f"[bold red]❌ PromptToBlock error:[/bold red] {e}")
                with open(DEBUG_LOG, "a") as f:
                    f.write("\n--- PromptToBlock Error ---\n")
                    f.write(traceback.format_exc())
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
        client = OpenAI(api_key=api_key)

        def classify(msg: str) -> str:
            prompt = f"""Classify the sentiment of the following text as Positive, Negative, or Neutral.\nText: "{msg}"\nSentiment:"""
            try:
                response = client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0
                )
                return response.choices[0].message.content.strip()
            except Exception as e:
                rprint(
                    f"[bold red]❌ SentimentClassifier error:[/bold red] {e}")
                with open(DEBUG_LOG, "a") as f:
                    f.write("\n--- SentimentClassifierWithGPT Error ---\n")
                    f.write(traceback.format_exc())
                return "error"

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
        client = OpenAI(api_key=api_key)

        def extract(msg: str) -> list[str]:
            prompt = f"""Extract named entities from the text as a Python list.\nText: "{msg}" """
            try:
                response = client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                )
                text = response.choices[0].message.content.strip()
                return ast.literal_eval(text) if text.startswith("[") else []
            except Exception as e:
                rprint(f"[bold red]❌ ExtractEntities error:[/bold red] {e}")
                with open(DEBUG_LOG, "a") as f:
                    f.write("\n--- ExtractEntitiesWithGPT Error ---\n")
                    f.write(traceback.format_exc())
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
        client = OpenAI(api_key=api_key)

        def summarize(text: str) -> str:
            prompt = f"Summarize the following in no more than {max_words} words:\n\n{text}"
            try:
                response = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system",
                            "content": "You are a helpful assistant that summarizes text."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=temperature
                )
                return response.choices[0].message.content.strip()
            except Exception as e:
                rprint(f"[bold red]❌ SummarizeWithGPT error:[/bold red] {e}")
                with open(DEBUG_LOG, "a") as f:
                    f.write("\n--- SummarizeWithGPT Error ---\n")
                    f.write(traceback.format_exc())
                return "error"

        super().__init__(transform_fn=summarize, name="SummarizeWithGPT")

# =================================================
#        MergeSynch                |
# =================================================


class MergeSynch(Agent):
    """
    Block with multiple inports and one outport "out".
    Waits to receive one message from EACH inport synchronously in order,
    then applies transformer_fn([msg1, msg2, ...]) and sends the result to "out".
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

        super().__init__(name=name or "MergeSynch",
                         inports=inports,
                         outports=["out"],
                         run=self.run)

        self.transformer_fn = transformer_fn
        self.buffers = {port: [] for port in inports}

    def run(self):
        while True:
            for port in self.inports:
                msg = self.recv(port)
                print(f"in merge_synch, msg = {msg}")
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
                    rprint(
                        f"[bold red]❌ TransformMultipleStreams error:[/bold red] {e}")
                    with open(DEBUG_LOG, "a") as f:
                        f.write("\n--- TransformMultipleStreams Error ---\n")
                        f.write(traceback.format_exc())
                    self.send("__STOP__", "out")


# =================================================
#        MergeAsynch            |
# =================================================


class MergeAsynch(Agent):
    """
    Block with multiple inports and one outport "out".
    Processes messages as they arrive from ANY inport (asynchronously).
    Applies transformer_fn(msg, port) and sends result to "out".
    """

    def __init__(
        self,
        inports: list[str],
        transformer_fn: Optional[Callable[[Any, str], Any]] = None,
        name: Optional[str] = None
    ):
        if not inports:
            raise ValueError(
                "MergeAsynch requires at least one inport.")
        if transformer_fn is not None and not callable(transformer_fn):
            raise TypeError("transformer_fn must be a callable or None.")

        super().__init__(name=name or "MergeAsynch",
                         inports=inports,
                         outports=["out"],
                         run=self.run)

        self.transformer_fn = transformer_fn

        self.terminated_inports = {inport: False for inport in self.inports}

    def run(self):
        self.terminated_inports = {port: False for port in self.inports}

        while True:
            msg, port = self.wait_for_any_port()

            if msg == "__STOP__":
                self.terminated_inports[port] = True

                if all(self.terminated_inports[p] for p in self.inports):
                    self.send("__STOP__", "out")
                    return

                # Do not process a __STOP__ message
                continue

            try:
                result = self.transformer_fn(
                    msg, port) if self.transformer_fn else msg
                self.send(result, "out")
            except Exception as e:
                rprint(
                    f"[bold red]❌ MergeAsynch error:[/bold red] {e}")
                with open(DEBUG_LOG, "a") as f:
                    f.write("\n--- TransformMultipleStreams Error ---\n")
                    f.write(traceback.format_exc())
                self.send("__STOP__", "out")


# =================================================
#                     Broadcast                   |
# =================================================

class Broadcast(Agent):
    """
    Broadcasts any message received on inport "in" to all defined outports.
    Useful for duplicating a stream to multiple downstream blocks.
    """

    def __init__(
        self,
        outports: list[str],
        name: Optional[str] = None
    ):
        super().__init__(name=name or "Broadcast",
                         inports=["in"],
                         outports=outports,
                         run=self.run)

    def run(self):
        while True:
            msg = self.recv("in")
            if msg == "__STOP__":
                self.stop()
                return
            else:
                for outport in self.outports:
                    self.send(msg=msg, outport=outport)


# =================================================
#                   transform                     |
# =================================================


def transform(fn, *args, **kwargs):
    """
    Create a transformer block from a Python function.

    Examples:
    >>> transform(str.upper)
    >>> transform(lambda x, prefix=">> ": prefix + x, prefix=">> ")
    """
    if not callable(fn):
        raise TypeError(f"transform(fn) must be callable, got {type(fn)}")
    return WrapFunction(fn, args=args, kwargs=kwargs)
