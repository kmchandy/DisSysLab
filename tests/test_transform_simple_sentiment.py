# tests/test_transform.py
from __future__ import annotations
from typing import Any
from dsl.core import STOP
from dsl.block_lib.transforms.transform import Transform
from dsl.block_lib.transforms.transform_lib.simple_sentiment import add_sentiment, sentiment_score, label_from_score


class _Probe:
    def __init__(self):
        self.out = []

    def send(self, msg: Any, outport: str = "out"):
        assert outport == "out"
        self.out.append(msg)


def test_transform_maps_values():
    t = Transform(func=lambda m: m * 2)
    probe = _Probe()
    t.handle_msg(probe, 3)
    t.handle_msg(probe, -1)
    assert probe.out == [6, -2]


def test_transform_simple_sentiment():

    # Create a Transform that computes sentiment score and label
    sentiment_transform = Transform(func=add_sentiment)

    probe = _Probe()

    # Test messages
    messages = [
        {"text": "The team wins the championship!"},
        {"text": "There are concerns about the economy."},
        {"text": "The weather is neutral today."}
    ]

    for msg in messages:
        sentiment_transform.handle_msg(probe, msg)

    expected_outputs = [
        {'text': 'The team wins the championship!', 'sentiment': 'Positive'},
        {'text': 'There are concerns about the economy.', 'sentiment': 'Negative'},
        {'text': 'The weather is neutral today.', 'sentiment': 'Neutral'}
    ]

    t = Transform(func=add_sentiment)
    probe = _Probe()
    for message in messages:
        t.handle_msg(probe, message)
    assert probe.out == expected_outputs


if __name__ == "__main__":
    test_transform_simple_sentiment()
