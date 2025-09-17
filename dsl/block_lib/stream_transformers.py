"""
Module: stream_transformers.py

Summary:
Defines the StreamTransformer class and several variants for transforming data
streams. These include wrappers for arbitrary Python functions, multi-stream
transformations, and GPT-based transformations using OpenAI's API.

Tags: ["transformer", "stream", "block", "NLP", "OpenAI", "NumPy", "GPT"]
"""

import re as _re
from typing import Optional, Any, Callable
import os
import traceback
from rich import print as rprint

from dsl.core import SimpleAgent, Agent

DEBUG_LOG = "dsl_debug.log"

# =================================================
#        TransformerFunction                      |
# =================================================


class TransformerFunction(SimpleAgent):
    """
    Apply `func(msg)` to each incoming message and emit the result.

    If `input_key` is provided and incoming messages are dicts:
      - read value = msg[input_key]
      - result = func(value)
      - if `output_key` is provided: out = {**msg, output_key: result}
        else:                         out = {**msg, input_key: result}
      - emit `out`

    If `input_key` is None:
      - result = func(msg)
      - emit `result`
    """

    def __init__(
        self,
        func: Callable[[Any], Any],
        args: Optional[tuple] = (),
        kwargs: Optional[dict] = None,
        input_key: Optional[str] = None,
        output_key: Optional[str] = None,
        name: Optional[str] = None,
    ):
        kwargs = kwargs or {}

        def handle_msg(agent, msg):
            try:
                if input_key is not None and isinstance(msg, dict):
                    value = msg.get(input_key)
                    result = func(value, *args, **kwargs)
                    out_msg = dict(msg)  # shallow copy
                    out_msg[output_key or input_key] = result
                    agent.send(out_msg, "out")
                else:
                    result = func(msg, *args, **kwargs)
                    agent.send(result, "out")
            except Exception as e:
                # Keep the network resilient; surface error and continue.
                print(f"[TransformerFunction] Error: {e}")
                # You can choose to emit a sentinel or drop; here we drop.
                # agent.send("__STOP__", "out")

        super().__init__(
            name=name or "TransformerFunction",
            inport="in",
            outports=["out"],
            handle_msg=handle_msg,
        )


# =================================================
#        Get the OpenAI key                       |
# =================================================

def _resolve_openai_key() -> Optional[str]:
    # Try your helper first (loads .env too)
    try:
        from dsl.utils.get_credentials import get_openai_key
        return get_openai_key()  # raises if missing
    except Exception:
        # Fall back to raw env var; don’t crash yet
        return os.environ.get("OPENAI_API_KEY")


# =================================================
#        TransformerPrompt (GPT-backed)
#        (subclass of TransformerFunction)
# =================================================

# Assumes TransformerFunction is defined as in your latest version
# from dsl.block_lib.stream_transformers import TransformerFunction

class OpenAI_Block(SimpleAgent):
    def __init__(self,
                 *,
                 system_prompt: str,
                 model: str = "gpt-4o-mini",
                 temperature: float = 0.7,
                 name: Optional[str] = "OpenAI_Block"):
        super().__init__(
            name=name or "OpenAI_Block",
            inport="in",
            outports=["out"],
            init_fn=self.init_fn
            handle_msg=self.handle_msg
        )

        def init_fn(self):
            if not system_prompt:
                raise ValueError("system_prompt must be a non-empty string.")
            try:
                from openai import OpenAI
            except ImportError as e:
                raise ImportError(
                    "OpenAI client not installed. Install with: pip install -e '.[gpt]'"
                ) from e

            # Resolve API key
            key = _resolve_openai_key()
            if not key:
                raise ValueError(
                    "OpenAI API key not found. Set OPENAI_API_KEY in your environment "
                    "or configure dsl/utils/get_credentials.py (.env supported)."
                )
            # Store the key once on self
            self._client = OpenAI(api_key=key)

        def handle_msg(self, msg):
            resp = self._client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": str(msg_text)},
                ],
                temperature=temperature,
            )
            return resp.choices[0].message.content


class TransformerPrompt(TransformerFunction):
    """
    GPT-backed transformer with a fixed system prompt.

    - system_prompt: fixed instruction for the model (unchanging per block)
    - For each incoming message, the block sends:
        [ {"role": "system", "content": system_prompt},
          {"role": "user",   "content": <msg_text>} ]
    - If input_key/output_key are provided and msg is a dict:
        * read from msg[input_key]
        * write result to msg[output_key]
      Otherwise operate on plain strings.

    Requires OPENAI_API_KEY in the environment.
    """

    def __init__(self, *, system_prompt: str, model: str = "gpt-4o-mini",
                 temperature: float = 0.7, input_key: Optional[str] = None,
                 output_key: Optional[str] = None, name: Optional[str] = None):

        if not system_prompt:
            raise ValueError("system_prompt must be a non-empty string.")

        try:
            from openai import OpenAI
        except ImportError as e:
            raise ImportError(
                "OpenAI client not installed. Install with: pip install -e '.[gpt]'"
            ) from e

        # Resolve API key
        key = _resolve_openai_key()
        if not key:
            raise ValueError(
                "OpenAI API key not found. Set OPENAI_API_KEY in your environment "
                "or configure dsl/utils/get_credentials.py (.env supported)."
            )

        # Store the client once on self
        self._client = OpenAI(api_key=key)

        # GPT call function
        def _call_gpt(msg_text: str) -> str:
            resp = self._client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": str(msg_text)},
                ],
                temperature=temperature,
            )
            return resp.choices[0].message.content

        # Pass function to parent class
        super().__init__(func=_call_gpt,
                         input_key=input_key,
                         output_key=output_key,
                         name=name or "TransformerPrompt")


# =================================================
#       helper function: get_value_for_key        |
# =================================================

def get_value_for_key(key: str):
    """
    Returns a function that extracts the value corresponding to the given key from a message dictionary.

    Parameters:
        key (str): The key to extract from the input dictionary.

    Returns:
        Callable[[dict], Any]: A function that takes a dictionary and returns the value for the specified key.

    Example:
        >>> f = get_value_for_key("key_1")
        >>> f({"key_0": 5, "key_1": "A", "key_2": 100})
        'A'
    """
    def extractor(msg: dict):
        if not isinstance(msg, dict):
            raise ValueError(f"Expected msg to be a dict, got {type(msg)}")
        if key not in msg:
            raise KeyError(f"Key '{key}' not found in message: {msg}")
        return msg[key]

    return extractor


# =================================================
#                   transform                     |
# =================================================

def transform(func, *args, **kwargs):
    """
    Create a transformer block from a Python function.

    Examples:
    >>> transform(str.upper)
    >>> transform(lambda x, prefix=">> ": prefix + x, prefix=">> ")
    """
    if not callable(func):
        raise TypeError(f"transform(func) must be callable, got {type(func)}")
    # dsl/block_lib/stream_transformers.py
    return TransformerFunction(func, args=args, kwargs=kwargs)
