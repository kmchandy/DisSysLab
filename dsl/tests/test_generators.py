"""
Unit tests for the simplified record() function in stream_recorders.py.
"""

import os
import tempfile
from pathlib import Path
from dsl.core import Network
from dsl.block_lib.stream_generators import generate
from dsl.block_lib.stream_recorders import record


def test_record_to_memory():
    gen = generate(["apple", "banana"])
    sink = record(to="memory")
    net = Network(
        name="test_memory",
        blocks={"gen": gen, "sink": sink},
        connections=[("gen", "out", "sink", "in")]
    )
    net.compile()
    net.run()
    assert hasattr(sink, "saved")
    assert sink.saved == ["apple", "banana"]


def test_record_to_file():
    fd, path = tempfile.mkstemp()
    os.close(fd)
    try:
        gen = generate(["dog", "cat"])
        sink = record(to=path)
        net = Network(
            name="test_file",
            blocks={"gen": gen, "sink": sink},
            connections=[("gen", "out", "sink", "in")]
        )
        net.compile()
        net.run()
        with open(path, "r") as f:
            lines = [line.strip() for line in f]
        assert lines == ["dog", "cat"]
    finally:
        os.remove(path)


def test_record_to_file_stream():
    fd, path = tempfile.mkstemp()
    os.close(fd)
    try:
        gen = generate(["snap", "crackle"])
        tap = record(to="file+stream", filepath=path)
        sink = record(to="memory")
        net = Network(
            name="test_file_stream",
            blocks={"gen": gen, "tap": tap, "sink": sink},
            connections=[
                ("gen", "out", "tap", "in"),
                ("tap", "out", "sink", "in")
            ]
        )
        net.compile()
        net.run()
        assert sink.saved == ["snap", "crackle"]
        with open(path, "r") as f:
            logged = [line.strip() for line in f]
        assert logged == ["'snap'", "'crackle'"]
    finally:
        os.remove(path)


def test_record_pathlib_support():
    fd, path = tempfile.mkstemp()
    os.close(fd)
    try:
        gen = generate(["a", "b"])
        sink = record(to=Path(path))
        net = Network(
            name="test_pathlib",
            blocks={"gen": gen, "sink": sink},
            connections=[("gen", "out", "sink", "in")]
        )
        net.compile()
        net.run()
        with open(path, "r") as f:
            lines = [line.strip() for line in f]
        assert lines == ["a", "b"]
    finally:
        os.remove(path)


def test_record_invalid_to_argument():
    try:
        record(to=123)
        assert False, "Expected ValueError for invalid 'to'"
    except ValueError:
        pass


def test_record_file_stream_missing_filepath():
    try:
        record(to="file+stream")
        assert False, "Expected ValueError when 'filepath' is missing"
    except ValueError:
        pass


def test_generate_from_list():
    gen = generate(["one", "two"])
    sink = record()
    net = Network(
        name="test_generate_list",
        blocks={"gen": gen, "sink": sink},
        connections=[("gen", "out", "sink", "in")]
    )
    net.compile()
    net.run()
    assert sink.saved == ["one", "two"]


if __name__ == "__main__":
    test_record_to_memory()
    test_record_to_file()
    test_record_to_file_stream()
    test_record_pathlib_support()
    test_record_invalid_to_argument()
    test_record_file_stream_missing_filepath()
    test_generate_from_list()
    print("✅ All record(...) generator tests passed.")
