# dsl/tests/test_generators.py

import os
import tempfile
import pytest
from dsl.core import Network
from dsl.block_lib.stream_generators import generate
from dsl.block_lib.stream_recorders import record


def f(n):
    for i in range(n):
        yield i


def test_generate_from_list():
    net = Network(
        blocks={
            "source": generate(["a", "b", "c"]),
            "sink": record()
        },
        connections=[("source", "out", "sink", "in")]
    )
    net.compile_and_run()
    assert net.blocks["sink"].saved == ["a", "b", "c"]


def test_generate_from_file():
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


def test_generate_from_python_generator():
    net = Network(
        blocks={
            "source": generate(f, n=3),
            "sink": record()
        },
        connections=[("source", "out", "sink", "in")]
    )
    net.compile_and_run()
    assert net.blocks["sink"].saved == [0, 1, 2]


def test_generate_empty_list():
    net = Network(
        blocks={
            "source": generate([]),
            "sink": record()
        },
        connections=[("source", "out", "sink", "in")]
    )
    net.compile_and_run()
    assert net.blocks["sink"].saved == []


def test_generate_single_item():
    net = Network(
        blocks={
            "source": generate(["only"]),
            "sink": record()
        },
        connections=[("source", "out", "sink", "in")]
    )
    net.compile_and_run()
    assert net.blocks["sink"].saved == ["only"]


def test_generate_invalid_source_type():
    with pytest.raises(TypeError):
        generate(123)  # not a list or callable


def repeat(text, times=2):
    for _ in range(times):
        yield text


def test_generate_with_args_and_kwargs():
    net = Network(
        blocks={
            "source": generate(repeat, text="hello", times=3),
            "sink": record()
        },
        connections=[("source", "out", "sink", "in")]
    )
    net.compile_and_run()
    assert net.blocks["sink"].saved == ["hello", "hello", "hello"]


def test_generate_with_delay():
    net = Network(
        blocks={
            "source": generate(["a", "b"], delay=0.01),
            "sink": record()
        },
        connections=[("source", "out", "sink", "in")]
    )
    net.compile_and_run()
    assert net.blocks["sink"].saved == ["a", "b"]


# def test_generate_runtime_error_logs():
#     def gen_with_runtime_error():
#         yield "start"
#         raise RuntimeError("boom")

#     net = Network(
#         blocks={
#             "source": generate(gen_with_runtime_error),
#             "sink": record()
#         },
#         connections=[("source", "out", "sink", "in")]
#     )

#     try:
#         net.compile_and_run()
#     except RuntimeError:
#         pass  # expected

#     with open("debug.log") as f:
#         assert "boom" in f.read()
