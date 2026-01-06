# dsl/decorators.py

from functools import wraps


def msg_map(input_keys, output_keys=None):
    """
    Decorator that maps dict messages to function arguments and return values back to dict messages.

    This decorator enables ordinary Python functions to work in a distributed network.
    Functions communicate by passing dict messages between each other.

    Args:
        input_keys: List of keys to extract from msg_in as arguments to the function.
                   The function will be called with these values as positional arguments.
        output_keys: List of keys to store the function's return values in msg_out.
                    If None or empty, treats the function as a sink (no return value).
                    For multiple return values, the function should return a tuple.

    Usage:
        # Transformer agent (has inputs and outputs)
        @msg_map(input_keys=["text"], output_keys=["clean_text"])
        def clean_text(text):
            return text.strip().lower()

        # Agent with multiple outputs
        @msg_map(input_keys=["text"], output_keys=["sentiment", "score"])
        def analyze_sentiment(text):
            sentiment = "positive" if "good" in text else "negative"
            score = 0.8
            return sentiment, score

        # Sink agent (has inputs but no outputs)
        @msg_map(input_keys=["text", "sentiment"])
        def display_results(text, sentiment):
            print(f"Text: {text}, Sentiment: {sentiment}")

        # Wrapping imported functions
        from mylib import analyze
        analyze = msg_map(input_keys=["data"], output_keys=["result"])(analyze)

    Returns:
        A decorator function that wraps the original function to work with dict messages.

    Notes:
        - All messages in the network are dicts
        - The decorator automatically extracts the needed values from incoming messages
        - Results are automatically packaged into outgoing messages
        - Other fields in the message dict are preserved (passed through)
        - Sink agents (output_keys=None) return None instead of a dict
        - The wrapper preserves the original function's __name__, __qualname__, and __doc__
    """
    def decorator(func):
        @wraps(func)  # Preserves __name__, __qualname__, __doc__, etc.
        def wrapper(msg_in):
            # Extract arguments from msg_in using input_keys
            args = [msg_in[key] for key in input_keys]

            # Call the original function
            result = func(*args)

            # If no output_keys, this is a sink - return None
            if not output_keys:
                return None

            # Handle single vs multiple return values
            if not isinstance(result, tuple):
                result = (result,)

            # Create msg_out with results mapped to output_keys
            msg_out = msg_in.copy()  # Preserve other fields from msg_in
            for key, value in zip(output_keys, result):
                msg_out[key] = value

            return msg_out

        return wrapper
    return decorator
