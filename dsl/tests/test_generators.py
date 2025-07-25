# dsl/tests/test_generators.py

import os
import tempfile

from dsl.block_lib.stream_generators import (
    generate,
    GenerateFromList,
    GenerateFromFile,
)
from dsl.block_lib.stream_recorders import record
from dsl.core import Network


def test_generate_from_list():
    net = Network(
        blocks={
            "source": generate(["a", "b", "c"]),
            "sink": record()
        },
        connections=[
            ("source", "out", "sink", "in")
        ]
    )

    net.compile_and_run()
    assert net.blocks["sink"].saved == ["a", "b", "c"]


def test_generate_from_file():
    with tempfile.NamedTemporaryFile(mode="w+", delete=False) as f:
        f.write("apple\nbanana\ncarrot\n")
        f_path = f.name

    try:
        net = Network(
            blocks={
                "source": generate(filename=f_path),
                "sink": record()
            },
            connections=[
                ("source", "out", "sink", "in")
            ]
        )

        net.compile_and_run()
        assert net.blocks["sink"].saved == ["apple", "banana", "carrot"]
    finally:
        os.remove(f_path)


def test_generate_from_list_direct():
    block = GenerateFromList(items=["x", "y"])
    assert block.name.startswith("GenerateFromList")
    assert block.generator_fn is not None


def test_generate_from_file_direct(tmp_path):
    file_path = tmp_path / "data.txt"
    file_path.write_text("1\n2\n3\n")
    block = GenerateFromFile(filename=str(file_path))
    assert block.name.startswith("GenerateFromFile")
    assert block.generator_fn is not None


def test_generate_empty_list():
    net = Network(
        blocks={
            "source": generate([]),
            "sink": record()
        },
        connections=[
            ("source", "out", "sink", "in")
        ]
    )

    net.compile_and_run()
    assert net.blocks["sink"].saved == []


def test_generate_single_item():
    net = Network(
        blocks={
            "source": generate(["one"]),
            "sink": record()
        },
        connections=[
            ("source", "out", "sink", "in")
        ]
    )

    net.compile_and_run()
    assert net.blocks["sink"].saved == ["one"]
