# dsl/decorators.py

"""
Decorators for wrapping ordinary Python functions into DSL agents.

Key principle: Functions being wrapped are general-purpose and know nothing 
about DSL, messages, or distributed systems. The decorators handle all the 
message passing infrastructure.
"""

from dsl.blocks.source import Source
from dsl.blocks.transform import Transform
from dsl.blocks.sink import Sink


def source_map(output_keys):
    """
    Wrap a generator function into a Source agent.

    The wrapped function should:
    - Take no arguments: fn()
    - Return a value or tuple of values
    - Return None when exhausted

    Args:
        output_keys: List of keys for the output message dict.
                    If empty list [], raw return value is sent (no dict wrapping).
                    If non-empty, return value(s) are packaged into dict.

    Returns:
        Source agent that generates messages

    Examples:
        # Returns single values, wrap in dict
        >>> class Counter:
        ...     def __init__(self, n):
        ...         self.count = 0
        ...         self.n = n
        ...     def run(self):
        ...         if self.count >= self.n:
        ...             return None
        ...         val = self.count
        ...         self.count += 1
        ...         return val
        >>> 
        >>> counter = Counter(5)
        >>> source = source_map(output_keys=["value"])(counter.run)
        # Generates: {"value": 0}, {"value": 1}, ...

        # Returns multiple values
        >>> class PairGenerator:
        ...     def run(self):
        ...         return (1, 10)  # Returns tuple
        >>> 
        >>> gen = PairGenerator()
        >>> source = source_map(output_keys=["x", "y"])(gen.run)
        # Generates: {"x": 1, "y": 10}

        # No dict wrapping (future flexibility)
        >>> source = source_map(output_keys=[])(simple_gen.run)
        # Generates: raw values, not dicts
    """
    def decorator(func):
        def wrapper():
            result = func()

            if result is None:
                return None

            # If no output_keys, pass through raw value
            if not output_keys:
                return result

            # Convert to tuple if needed
            if not isinstance(result, tuple):
                result = (result,)

            # Package into dict
            msg_out = {}
            for key, value in zip(output_keys, result):
                msg_out[key] = value

            return msg_out

        wrapper.__name__ = func.__name__
        return Source(fn=wrapper)

    return decorator


def transform_map(input_keys, output_keys):
    """
    Wrap a processing function into a Transform agent.

    The wrapped function should:
    - Take arguments corresponding to input_keys
    - Return value(s) corresponding to output_keys
    - Know nothing about message dicts

    Args:
        input_keys: List of keys to extract from incoming message.
                   If empty list [], raw message is passed to function.
        output_keys: List of keys for storing results in outgoing message.
                    If empty list [], raw return value becomes the message.

    Returns:
        Transform agent that processes messages

    Examples:
        # Simple transform
        >>> def clean_text(text):
        ...     return text.strip().lower()
        >>> 
        >>> clean = transform_map(
        ...     input_keys=["text"],
        ...     output_keys=["clean_text"]
        ... )(clean_text)
        # Input:  {"text": "  HELLO  "}
        # Output: {"text": "  HELLO  ", "clean_text": "hello"}

        # Multiple inputs and outputs
        >>> def analyze(text):
        ...     sentiment = "positive" if "good" in text else "negative"
        ...     score = 0.8
        ...     return sentiment, score
        >>> 
        >>> analyzer = transform_map(
        ...     input_keys=["clean_text"],
        ...     output_keys=["sentiment", "score"]
        ... )(analyze)
        # Input:  {"clean_text": "this is good"}
        # Output: {"clean_text": "this is good", "sentiment": "positive", "score": 0.8}
    """
    def decorator(func):
        def wrapper(msg_in):
            # Extract inputs from message
            if not input_keys:
                # No dict unwrapping - pass raw message
                args = [msg_in]
            else:
                args = [msg_in[key] for key in input_keys]

            # Call the function
            result = func(*args)

            # Handle output
            if not output_keys:
                # No dict wrapping - return raw result
                return result

            # Convert to tuple if needed
            if not isinstance(result, tuple):
                result = (result,)

            # Check for None (filter pattern)
            if result == (None,) or any(v is None for v in result):
                return None

            # Create output message (preserve input fields)
            msg_out = msg_in.copy()
            for key, value in zip(output_keys, result):
                msg_out[key] = value

            return msg_out

        wrapper.__name__ = func.__name__
        return Transform(fn=wrapper)

    return decorator


def sink_map(input_keys):
    """
    Wrap a consumer function into a Sink agent.

    The wrapped function should:
    - Take arguments corresponding to input_keys
    - Not return anything (or return value is ignored)
    - Know nothing about message dicts

    Args:
        input_keys: List of keys to extract from incoming message.
                   If empty list [], raw message is passed to function.

    Returns:
        Sink agent that consumes messages

    Examples:
        # Simple print sink
        >>> def print_result(text, sentiment):
        ...     print(f"{text}: {sentiment}")
        >>> 
        >>> display = sink_map(
        ...     input_keys=["text", "sentiment"]
        ... )(print_result)
        # Receives: {"text": "hello", "sentiment": "positive"}
        # Prints: "hello: positive"

        # Single input
        >>> def save_to_db(data):
        ...     database.save(data)
        >>> 
        >>> saver = sink_map(input_keys=["data"])(save_to_db)
    """
    def decorator(func):
        def wrapper(msg_in):
            # Extract inputs from message
            if not input_keys:
                # No dict unwrapping - pass raw message
                args = [msg_in]
            else:
                args = [msg_in[key] for key in input_keys]

            # Call the function (return value ignored for sinks)
            func(*args)
            return None

        wrapper.__name__ = func.__name__
        return Sink(fn=wrapper)

    return decorator


__all__ = ["source_map", "transform_map", "sink_map"]
