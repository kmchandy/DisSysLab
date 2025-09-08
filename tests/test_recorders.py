import os
import json
import tempfile
import pytest
from dsl.core import Network
from dsl.block_lib.stream_generators import generate
from dsl.block_lib.stream_recorders import (
    Record,
    RecordToFile,
    RecordToList,
    RecordToConsole,
    RecordToLogFile,
    record,
)

# TEST 1


def test_record_to_list_entire_msg():
    results = []
    net = Network(
        blocks={
            "gen": generate(source=["one", "two"], key="data"),
            "rec": RecordToList(results),
        },
        connections=[("gen", "out", "rec", "in")],
    )

    net.compile_and_run()

    assert results == [{"data": "one"}, {"data": "two"}]

# TEST 2


def test_record_to_list_with_key():
    results = []

    net = Network(
        blocks={
            "gen": generate(["apple", "banana"]),
            "rec": RecordToList(results, key="data"),
        },
        connections=[("gen", "out", "rec", "in")],
    )
    net.compile_and_run()

    assert results == ["apple", "banana"]

# TEST 3


def test_record_to_file_with_key():
    with tempfile.NamedTemporaryFile(delete=False, mode="r+") as tmp:
        tmp.close()
        net = Network(
            blocks={
                "gen": generate(["x", "y"], key="sentiment"),
                "rec": RecordToFile(tmp.name, key="sentiment"),
            },
            connections=[("gen", "out", "rec", "in")],
        )
        net.compile_and_run()

        with open(tmp.name, "r") as f:
            lines = [json.loads(line.strip()) for line in f.readlines()]
        assert lines == ["x", "y"]
    os.unlink(tmp.name)

# TEST 4


def test_record_to_file_entire_msg():
    with tempfile.NamedTemporaryFile(delete=False, mode="r+") as tmp:
        tmp.close()
        messages = [1, 2]
        net = Network(
            blocks={
                "gen": generate(messages),
                "rec": RecordToFile(tmp.name),
            },
            connections=[("gen", "out", "rec", "in")],
        )
        net.compile_and_run()
        with open(tmp.name, "r") as f:
            lines = [json.loads(line.strip()) for line in f.readlines()]
        assert lines == messages
    os.unlink(tmp.name)


# TEST 5

def test_record_to_logfile(tmp_path):
    base_path = tmp_path / "mylog"
    block = RecordToLogFile(str(base_path), key="data")

    net = Network(
        blocks={
            "gen": generate(["a", "b"]),
            "rec": block,
        },
        connections=[("gen", "out", "rec", "in")],
    )

    net.compile_and_run()

    # Locate the file just created
    log_files = list(tmp_path.glob("mylog_*.log"))

    assert len(log_files) == 1

    with open(log_files[0]) as f:
        lines = [json.loads(line.strip()) for line in f.readlines()]
    assert lines == ["a", "b"]


# TEST 6

def test_record_short_form():
    results = []

    net = Network(
        blocks={
            "gen": generate(["one", "two"], key="data"),
            "rec": record(to="list", target=results, key="data")
        },
        connections=[("gen", "out", "rec", "in")]
    )

    net.compile_and_run()
    print(results)
    assert results == ["one", "two"]


if __name__ == "__main__":
    test_record_to_list_entire_msg()
    test_record_to_list_with_key()
    test_record_to_file_with_key()
    test_record_to_file_entire_msg()
    # test_record_to_console(monkeypatch)
    # test_record_to_logfile(tmp_path=./)
