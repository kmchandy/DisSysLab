# /tests/test_transform.py
from __future__ import annotations
from typing import Any
from dsl.block_lib.transforms.transform import Transform
from dsl.block_lib.transforms.transform_lib.simple_entity_extractor import extract_entity


class _Probe:
    def __init__(self):
        self.out = []

    def send(self, msg: Any, outport: str = "out"):
        assert outport == "out"
        self.out.append(msg)


def test_transform_simple_entity_extractor():

    probe = _Probe()

    # Test messages
    messages = [
        {"text": "Obama was the President of the USA in 2016."},
        {"text": "Brazil, India, China and South Africa are part of Brics."},
        {"text": "Mount Everest is the highest mountain in the world."}
    ]
    expected_outputs = [
        {'text': 'Obama was the President of the USA in 2016.',
         'entities':
            {'people & objects': ['President', 'Obama'],
             'places': []}},
        {'text': 'Brazil, India, China and South Africa are part of Brics.',
         'entities':
            {'people & objects': ['Brics'],
             'places': ['China', 'South Africa', 'Brazil', 'India']}},
        {'text': 'Mount Everest is the highest mountain in the world.',
         'entities':
             {'people & objects': [],
              'places': ['Mount Everest']}}]
    t = Transform(func=extract_entity)
    probe = _Probe()
    for message in messages:
        t.handle_msg(probe, message)
    print(f"probe.out = {probe.out}")
    assert probe.out == expected_outputs


if __name__ == "__main__":
    test_transform_simple_entity_extractor()
