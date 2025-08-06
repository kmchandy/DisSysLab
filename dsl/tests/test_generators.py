# dsl/tests/test_generators.py

import os
import tempfile
import pytest
from dsl.core import Network
from dsl.block_lib.stream_generators import generate
from dsl.block_lib.stream_recorders import RecordToList


def f(n):
    for i in range(n):
        yield i


def test_generate_from_list():
    results = []

    net = Network(
        blocks={
            "source": generate(["a", "b", "c"]),
            "sink": RecordToList(results),
        },
        connections=[("source", "out", "sink", "in")]
    )
    net.compile_and_run()
    assert results == ["a", "b", "c"]


def test_generate_from_file():
    results = []

    with tempfile.NamedTemporaryFile(mode="w+", delete=False) as f:
        f.write("apple\nbanana\ncarrot\n")
        f_path = f.name

    def read_file():
        with open(f_path) as file:
            return [line.strip() for line in file]

    try:
        net = Network(
            blocks={
                "source": generate(read_file),
                "sink": RecordToList(results),
            },
            connections=[
                ("source", "out", "sink", "in")
            ]
        )

        net.compile_and_run()
        assert results == ["apple", "banana", "carrot"]
    finally:
        os.remove(f_path)


def test_generate_from_python_generator():
    results = []

    net = Network(
        blocks={
            "source": generate(f, n=3),
            "sink": RecordToList(results),
        },
        connections=[("source", "out", "sink", "in")]
    )
    net.compile_and_run()
    assert results == [0, 1, 2]


def test_generate_empty_list():
    results = []

    net = Network(
        blocks={
            "source": generate([]),
            "sink": RecordToList(results),
        },
        connections=[("source", "out", "sink", "in")]
    )
    net.compile_and_run()
    assert results == []


def test_generate_single_item():
    results = []

    net = Network(
        blocks={
            "source": generate(["only"]),
            "sink": RecordToList(results),
        },
        connections=[("source", "out", "sink", "in")]
    )
    net.compile_and_run()
    assert results == ["only"]


def test_generate_invalid_source_type():
    with pytest.raises(TypeError):
        generate(123)  # not a list or callable


def repeat(text, times=2):
    for _ in range(times):
        yield text


def test_generate_with_args_and_kwargs():
    results = []

    net = Network(
        blocks={
            "source": generate(repeat, text="hello", times=3),
            "sink": RecordToList(results),
        },
        connections=[("source", "out", "sink", "in")]
    )
    net.compile_and_run()
    assert results == ["hello", "hello", "hello"]


def test_generate_with_delay():
    results = []

    net = Network(
        blocks={
            "source": generate(["a", "b"], delay=0.01),
            "sink": RecordToList(results),
        },
        connections=[("source", "out", "sink", "in")]
    )
    net.compile_and_run()
    assert results == ["a", "b"]
