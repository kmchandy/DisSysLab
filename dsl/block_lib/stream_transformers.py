"""
Module: stream_transformers.py

Summary:
Defines the StreamTransformer class and several variants for transforming data
streams. These include wrappers for arbitrary Python functions, multi-stream
transformations, and GPT-based transformations using OpenAI's API.

Tags: ["transformer", "stream", "block", "NLP", "OpenAI", "NumPy", "GPT"]
"""

from __future__ import annotations
from dsl.core import SimpleAgent
from typing import Any, Callable, Optional, Dict
from typing import Optional, Any, Callable
import os
import traceback
from rich import print as rprint

from dsl.core import SimpleAgent, Agent

DEBUG_LOG = "dsl_debug.log"


# =================================================
#    TransformerFunction(SimpleAgent)             |
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

# assumes TransformerFunction is defined as in your latest version
# from dsl.block_lib.stream_transformers import TransformerFunction


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


class TransformerFunction(SimpleAgent):
    """
    Wrap a Python function as a block that transforms messages.

    - If input_key/output_key are given and msg is a dict:
        * read input value from msg[input_key]
        * write result to msg[output_key] (copy-on-write)
      Otherwise, treat msg itself as the value and emit the raw result.

    Example:
        tf = TransformerFunction(func=str.upper)
        tf will output "HELLO" for input "hello".
    """

    def __init__(
        self,
        *,
        func: Callable[[Any], Any],
        input_key: Optional[str] = None,
        output_key: Optional[str] = None,
        name: Optional[str] = "TransformerFunction",
    ) -> None:
        if not callable(func):
            raise TypeError("func must be callable")
        self._func = func
        self._in_key = input_key
        self._out_key = output_key

        # NOTE: instance-assigned handler → no implicit self
        def _handle(msg: Any, **_params: Dict[str, Any]) -> None:
            # dict routing
            if isinstance(msg, dict) and (self._in_key is not None or self._out_key is not None):
                if self._in_key is None or self._out_key is None:
                    raise ValueError(
                        f"{name}: both input_key and output_key must be set when using dict routing"
                    )
                if self._in_key not in msg:
                    raise KeyError(
                        f"{name}: input_key '{self._in_key}' not in message dict")
                value_in = msg[self._in_key]
                value_out = self._func(value_in)
                new_msg = dict(msg)
                new_msg[self._out_key] = value_out
                self.send(new_msg, outport="out")
                return

            # plain message routing
            result = self._func(msg)
            self.send(result, outport="out")

        super().__init__(name=name, inport="in",
                         outports=["out"], handle_msg=_handle)
