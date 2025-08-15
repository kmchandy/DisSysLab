"""
Module: stream_transformers.py

Summary:
Defines the StreamTransformer class and several variants for transforming data
streams. These include wrappers for arbitrary Python functions, multi-stream
transformations, and GPT-based transformations using OpenAI's API.

Tags: ["transformer", "stream", "block", "NLP", "OpenAI", "NumPy", "GPT"]
"""


from __future__ import annotations
from typing import Optional, Callable, Any, Iterable, Sequence, Union
from dsl.core import SimpleAgent


DEBUG_LOG = "dsl_debug.log"


# =================================================
#                     Broadcast                   |
# =================================================

class Broadcast(SimpleAgent):
    """
    Broadcasts any message received on inport "in" to all defined outports.
    Useful for duplicating a stream to multiple downstream blocks.
    """

    def __init__(self, outports: list[str], name: Optional[str] = None):

        def handle_msg(agent, msg):
            # Always propagate stop signal to all outports.
            if msg == "__STOP__":
                for p in outports:
                    agent.send("__STOP__", p)
                return
            # Otherwise, broadcast the message to all outports.
            for outport in outports:
                agent.send(msg=msg, outport=outport)

        super().__init__(
            name=name or "Broadcast",
            inport="in",
            outports=outports,
            handle_msg=handle_msg,
        )


# =================================================
#                     Split                       |
# =================================================

OutSel = Union[str, Iterable[str], None]


class Split(SimpleAgent):
    """
    Split: route each incoming message to one or more outports chosen by `split_function`.

    Parameters
    ----------
    split_function : Callable[[Any], Union[str, Iterable[str], None]]
        A function that receives the incoming `msg` and returns:
          - a single outport name (str), OR
          - a collection of outport names (list/tuple/set of str), OR
          - None to drop the message (route to no outport).
    outports : Sequence[str]
        The full set of outport names this block can emit to.
    name : Optional[str]
        Optional block name (defaults to "Split").

    Behavior
    --------
    - Messages are *not* modified; they’re simply forwarded (fan-out) to selected outports.
    - "__STOP__" is forwarded to *all* outports to help downstream blocks terminate cleanly.
    - If `split_function` returns an outport not in `outports`, a ValueError is raised
      (fail fast for student clarity).
    - Returning an empty collection or None results in the message being dropped.

    Example
    -------
    def positive_or_negative(msg):
        return "pos" if msg >= 0 else "neg"

    splitter = Split(
        split_function=positive_or_negative,
        outports=["pos", "neg"]
    )

    # For multi-route:
    def route_long_and_vowel(s: str):
        targets = []
        if len(s) > 5: targets.append("long")
        if any(ch in "aeiouAEIOU" for ch in s): targets.append("has_vowel")
        return targets

    splitter2 = Split(
        split_function=route_long_and_vowel,
        outports=["long", "has_vowel"]
    )
    """

    def __init__(
        self,
        *,
        split_function: Callable[[Any], OutSel],
        outports: Sequence[str],
        name: Optional[str] = None,
    ):
        if not callable(split_function):
            raise TypeError("split_function must be callable.")
        if not outports or not all(isinstance(p, str) and p for p in outports):
            raise ValueError(
                "outports must be a non-empty sequence of non-empty strings.")

        self._split_fn = split_function
        self._outport_set = set(outports)

        def handle_msg(agent, msg):
            # Always propagate stop signal to all outports.
            if msg == "__STOP__":
                for p in outports:
                    agent.send("__STOP__", p)
                return

            try:
                selection = self._split_fn(msg)

                # Normalize selection to a list of unique outport names.
                if selection is None:
                    return  # drop message (no route)

                if isinstance(selection, str):
                    targets = [selection]
                else:
                    # Accept any iterable of strings
                    try:
                        targets = list(selection)
                    except TypeError:
                        raise TypeError(
                            "split_function must return a str, an iterable[str], or None."
                        )

                # Validate targets
                unique_targets = []
                seen = set()
                for t in targets:
                    if not isinstance(t, str) or not t:
                        raise TypeError(
                            "All outport names must be non-empty strings.")
                    if t not in self._outport_set:
                        raise ValueError(
                            f"split_function chose unknown outport '{t}'. "
                            f"Valid outports: {sorted(self._outport_set)}"
                        )
                    if t not in seen:
                        unique_targets.append(t)
                        seen.add(t)

                # Route to each selected outport
                for t in unique_targets:
                    agent.send(msg, t)

            except Exception as e:
                # Keep the error visible for students; you may choose to re-raise instead.
                print(f"[Split] Error while routing message: {e}")
                # drop the message on error (or choose to re-raise)

        super().__init__(
            name=name or "Split",
            inport="in",
            outports=list(outports),
            handle_msg=handle_msg,
        )
