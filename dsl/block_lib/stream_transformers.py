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
from dsl.core import SimpleAgent, Agent

# =================================================
#          StreamTransformer                      |
# =================================================


class StreamTransformer(SimpleAgent):
    """
    Name: StreamTransformer

    Summary:
    Applies a transformation function to each incoming message.

    Parameters:
    - transform_fn: Callable for transforming each message.
    - args: Optional positional arguments.
    - kwargs: Optional keyword arguments.
    - name: Optional block name.
    - description: Optional description.

    Behavior:
    - Applies transform_fn(msg, *args, **kwargs).
    - Sends the result to "out".
    - Prints error and sends "__STOP__" if exception occurs.
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
    """
    Name: WrapFunction

    Summary:
    A subclass of StreamTransformer that wraps any Python function.

    Parameters:
    - func: Callable to wrap.
    - args: Optional positional args.
    - kwargs: Optional keyword args.
    - name: Optional name.
    - description: Optional description.

    Behavior:
    - Applies func to incoming messages.
    """

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
    """
    Name: PromptToBlock

    Summary:
    Sends a static or templated prompt to an OpenAI model and emits the response.

    Parameters:
    - prompt: Prompt template with optional {msg} placeholder.
    - model: OpenAI model name.
    - temperature: Sampling temperature.
    - name: Optional name.
    - description: Optional description.

    Example:
    >>> block = PromptToBlock(prompt="Summarize: {msg}", model="gpt-3.5-turbo")
    """

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
                response = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "user", "content": prompt.replace("{msg}", str(msg))}],
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
