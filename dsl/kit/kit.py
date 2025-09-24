# dsl/kit/kit.py
from __future__ import annotations
from typing import Iterable, Any, Dict
from dsl.blocks.source import Source
from dsl.blocks.transform import Transform
from dsl.blocks.sink import Sink
from dsl.core import Network  # adjust if Network lives elsewhere


def generate(fn, **params):
    return Source(fn=fn, params=params)


def transform(fn, **params):
    return Transform(fn=fn, params=params)


def record(fn, **params):
    return Sink(fn=fn, params=params)


def pipeline(blocks: Iterable[Any]) -> Network:
    blocks = list(blocks)
    blocks_map: Dict[str, Any] = {f"n{i}": b for i, b in enumerate(blocks)}
    connections = [(f"n{i}", "out", f"n{i+1}", "in")
                   for i in range(len(blocks)-1)]
    return Network(blocks=blocks_map, connections=connections)
