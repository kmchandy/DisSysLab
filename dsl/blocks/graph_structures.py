from __future__ import annotations
from typing import Sequence, Any
from dsl.core import Network


def pipeline(blocks: Sequence[Any]) -> Network:
    """
    Build a linear pipeline from an *ordered list* of block instances.
    Names are assigned automatically:
      - first  → "source"
      - last   → "sink"
      - middle → "transform_1", "transform_2", ...

    Example:
        net = pipeline_auto([FromList(["hello","world"]), Uppercase(), ToList(results)])

    Notes:
      - Requires at least two blocks (a source and a sink).
      - Assumes standard ports: "out" → "in".
    """
    n = len(blocks)
    if n < 2:
        raise ValueError(
            "pipeline_auto requires at least two blocks (source and sink).")

    name_list: list[str] = []
    block_dict: dict[str, Any] = {}

    for i, block in enumerate(blocks):
        if i == 0:
            name = "source"
        elif i == n - 1:
            name = "sink"
        else:
            name = f"transform_{i}"  # i starts at 1 for the first transform
        # ensure uniqueness just in case
        base = name
        k = 2
        while name in block_dict:
            name = f"{base}_{k}"
            k += 1
        block_dict[name] = block
        name_list.append(name)

    connections = [
        (name_list[i], "out", name_list[i + 1], "in")
        for i in range(n - 1)
    ]
    return Network(blocks=block_dict, connections=connections)
