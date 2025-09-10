# tests/test_transform_simple_sentiment.py
from __future__ import annotations
from typing import Any
from dsl.core import Network, Agent, STOP
from dsl.block_lib.sinks.sink import Sink
from dsl.block_lib.sources.source import Source
from dsl.block_lib.transforms.transform import Transform
from dsl.block_lib.transforms.transform_lib.simple_sentiment import add_sentiment
from dsl.block_lib.sinks.sink_lib.common_sinks import record_to_list
from dsl.block_lib.sources.source_lib.common_sources import gen_list


def test_transform_direct_values():
    results = []
    network = Network(
        blocks={
            "source": Source(generator_fn=gen_list(["A1", "A2", "__STOP__"])),
            "transform": Transform(func=lambda x: x),  # Identity transform
            "sink": Sink(record_fn=record_to_list(results))
        },
        connections=[
            ("source", "out", "transform", "in"),
            ("transform", "out", "sink", "in")
        ]
    )
    network.compile_and_run()
    assert results == ["A1", "A2"]


def test_transform_maps_values():
    t = Transform(func=lambda m: m * 2)
    probe = _Probe()
    t.handle_msg(probe, 3)
    t.handle_msg(probe, -1)
    assert probe.out == [6, -2]


def test_transform_simple_sentiment():

    # Create a Transform that computes sentiment score and label

    # Test messages
    messages = [
        {"text": "The team wins the championship!"},
        {"text": "There are concerns about the economy."},
        {"text": "The weather is the same today."}
    ]

    results = []
    network = Network(
        blocks={
            "source": Source(generator_fn=gen_list(messages + ["__STOP__"])),
            "transform": Transform(func=add_sentiment),
            "sink": Sink(record_fn=record_to_list(results))
        },
        connections=[
            ("source", "out", "transform", "in"),
            ("transform", "out", "sink", "in")
        ]
    )
    network.compile_and_run()

    assert results == [
        {'text': 'The team wins the championship!', 'sentiment': 'Positive'},
        {'text': 'There are concerns about the economy.', 'sentiment': 'Negative'},
        {'text': 'The weather is the same today.', 'sentiment': 'Neutral'}
    ]


if __name__ == "__main__":
    test_transform_direct_values()
    test_transform_simple_sentiment()
