# dsl/block_lib/transforms/transform_lib/simple_transform_classes.py
from dsl.block_lib.transforms.transform import Transform
from dsl.block_lib.transforms.transform_lib.simple_sentiment import (
    add_sentiment)
from typing import Optional, Iterable

__all__ = ["Uppercase", "AddSentiment"]


class Uppercase(Transform):
    """Transform that converts input text to uppercase."""

    def __init__(self,  name: str = "ToUpperCase"):
        super().__init__(func=lambda x: x.upper(), name=name)


class AddSentiment(Transform):
    """Add a sentiment label to each message (default looks at msg['text'])."""

    def __init__(
        self,
        *,
        input_key: str = "input_key",
        add_key: str = "sentiment",
        positive_words: Optional[Iterable[str]] = None,
        negative_words: Optional[Iterable[str]] = None,
        name: Optional[str] = None,
    ):
        super().__init__(
            func=add_sentiment,
            kwargs={
                "input_key": input_key,
                "add_key": add_key,
                "positive_words": positive_words,
                "negative_words": negative_words,
            },
            name=name or "AddSentiment",
        )
