"""
Module: stream_transformers.py

Summary:
Defines the StreamTransformer class and several variants for transforming data
streams. These include wrappers for arbitrary Python functions, multi-stream
transformations, and GPT-based transformations using OpenAI's API.

Tags: ["transformer", "stream", "block", "NLP", "OpenAI", "NumPy", "GPT"]
"""

from dsl.core import SimpleAgent  # adjust import if needed
from typing import Optional
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
    def __init__(
        self,
        transform_fn: Callable,
        args=(),
        kwargs=None,
        input_key: Optional[str] = None,
        output_key: Optional[str] = None,
        name: Optional[str] = None,
    ):
        if not name:
            name = "StreamTransformer"

        kwargs = kwargs or {}

        def handle_msg(agent, msg):
            print(f"[StreamTransformer.handle_msg] Received: {msg}")
            try:
                if input_key is not None and isinstance(msg, dict):
                    input_value = msg.get(input_key)
                    result = transform_fn(input_value, *args, **kwargs)
                    out_msg = dict(msg)  # shallow copy
                    if output_key:
                        out_msg[output_key] = result
                    else:
                        out_msg[input_key] = result
                    agent.send(msg=out_msg, outport="out")
                else:
                    # No input key, apply transform to whole msg
                    result = transform_fn(msg, *args, **kwargs)
                    agent.send(msg=result,  outport="out")
            except Exception as e:
                print(f"[StreamTransformer] Error: {e}")
                raise

        super().__init__(
            name=name,
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
        input_key: Optional[str] = None,
        output_key: Optional[str] = None,
        name: Optional[str] = None,
    ):
        super().__init__(
            transform_fn=func,
            args=args,
            kwargs=kwargs,
            input_key=input_key,
            output_key=output_key,
            name=name or "WrapFunction",
        )


# =================================================
#      GPT_Prompt(StreamTransformer)          |
# =================================================

class GPT_Prompt(StreamTransformer):
    def __init__(
        self,
        messages: Callable[[str], list[dict]],
        postprocess_fn: Optional[Callable[[str], Any]] = None,
        model: str = "gpt-3.5-turbo",
        temperature: float = 0.7,
        input_key: Optional[str] = None,
        output_key: Optional[str] = None,
        name: Optional[str] = "GPTTransformer"
    ):
        load_dotenv()
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY is missing in environment.")
        client = OpenAI(api_key=api_key)

        def call_gpt(msg: str) -> Any:
            try:
                response = client.chat.completions.create(
                    model=model,
                    messages=messages(msg),
                    temperature=temperature
                )
                text = response.choices[0].message.content.strip()
                return postprocess_fn(text) if postprocess_fn else text
            except Exception as e:
                rprint(f"[bold red]❌ GPTTransformer error:[/bold red] {e}")
                with open(DEBUG_LOG, "a") as f:
                    f.write("\n--- GPTTransformer Error ---\n")
                    f.write(traceback.format_exc())
                return "error"

        super().__init__(
            transform_fn=call_gpt,
            input_key=input_key,
            output_key=output_key,
            name=name,
        )


# =================================================
#         PromptToBlock (WrapPrompt)              |
# =================================================


class PromptToBlock(SimpleAgent):
    """
    Minimal GPT wrapper:
      - system_prompt is fixed per block.
      - For each incoming message (msg), we extract text and send it as the user message.
      - If input_key/output_key are provided and msg is a dict:
          * read text from msg[input_key]
          * write result to msg[output_key]
        Otherwise, operate on plain strings.

    Requires OPENAI_API_KEY in the environment.
    """

    def __init__(
        self,
        system_prompt: str,
        model: str = "gpt-4o-mini",
        temperature: float = 0.7,
        input_key: Optional[str] = None,
        output_key: Optional[str] = None,
        name: Optional[str] = None,
    ):
        if not system_prompt:
            raise ValueError("system_prompt must be a non-empty string.")

        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not set in environment.")

        client = OpenAI(api_key=api_key)

        def extract_text(incoming):
            if input_key and isinstance(incoming, dict):
                return incoming.get(input_key, "")
            return incoming

        def emit(agent, original_msg, reply_text: str):
            if output_key and isinstance(original_msg, dict):
                out = dict(original_msg)
                out[output_key] = reply_text
                agent.send(out, "out")
            else:
                agent.send(reply_text, "out")

        # -------- lifecycle hooks --------
        def init_fn(agent):
            agent._oai_client = client
            agent._oai_model = model
            agent._oai_temp = temperature
            agent._oai_system = system_prompt
            agent._extract_text = extract_text
            agent._emit = emit

        def handle_msg(agent, msg):
            if msg == "__STOP__":
                agent.send("__STOP__", "out")
                return
            try:
                msg_text = agent._extract_text(msg)
                resp = agent._oai_client.chat.completions.create(
                    model=agent._oai_model,
                    messages=[
                        {"role": "system", "content": agent._oai_system},
                        {"role": "user", "content": str(msg_text)},
                    ],
                    temperature=agent._oai_temp,
                )
                reply = (resp.choices[0].message.content or "").strip()
                agent._emit(agent, msg, reply)
            except Exception as e:
                # Keep failure behavior simple and visible
                print(f"[PromptToBlock] Error: {e}")
                agent.send("__STOP__", "out")

        super().__init__(
            name=name or "PromptToBlock",
            inport="in",
            outports=["out"],
            init_fn=init_fn,
            handle_msg=handle_msg,
        )


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
    return WrapFunction(func, args=args, kwargs=kwargs)
