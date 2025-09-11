# dsl/block_lib/transforms/transform_lib/simple_transform_classes.py
from dsl.block_lib.transforms.transform import Transform
from dsl.block_lib.transforms.transform_lib.simple_sentiment import (
    add_sentiment)

__all__ = ["Uppercase", "AddSentiment"]


class Uppercase(Transform):
    """Transform that converts input text to uppercase."""

    def __init__(self,  name: str = "ToUpperCase"):
        super().__init__(func=lambda x: x.upper(), name=name)


class AddSentiment(Transform):
    """Transform that adds a 'sentiment' field to input dicts based on 'text' field."""

    def __init__(self, name: str = "AddSentiment"):
        super().__init__(func=add_sentiment, name=name)
