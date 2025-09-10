# tests/test_transform_simple_entity_extractor.py
from __future__ import annotations
from typing import Any
from dsl.core import Network, Agent, STOP
from dsl.block_lib.sinks.sink import Sink
from dsl.block_lib.sources.source import Source
from dsl.block_lib.transforms.transform import Transform
from dsl.block_lib.transforms.transform_lib.simple_entity_extractor import extract_entity
from dsl.block_lib.sinks.sink_lib.common_sinks import record_to_list
from dsl.block_lib.sources.source_lib.common_sources import gen_list


def test_transform_simple_entity_extractor():
    # Test messages
    messages = [
        {"text": "Obama was the President of the USA."},
    ]
    expected_outputs = [{'text': 'Obama was the President of the USA.', 'entities': {
        'people': ['Obama', 'President'], 'places': ['USA']}}]

    results = []
    network = Network(
        blocks={
            "source": Source(generator_fn=gen_list(messages + ["__STOP__"])),
            "transform": Transform(func=extract_entity),
            "sink": Sink(record_fn=record_to_list(results))
        },
        connections=[
            ("source", "out", "transform", "in"),
            ("transform", "out", "sink", "in")
        ]
    )
    network.compile_and_run()

    assert results == expected_outputs


if __name__ == "__main__":
    test_transform_simple_entity_extractor()
