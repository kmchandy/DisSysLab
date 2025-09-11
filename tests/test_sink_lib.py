# tests/test_sink_lib.py
from __future__ import annotations

import json
import sys
import io
from pathlib import Path

from dsl.core import Network
from dsl.block_lib.sinks.sink import Sink
from dsl.block_lib.sources.source import Source
from dsl.block_lib.sources.source_lib.common_classes import FromList
from dsl.block_lib.sources.source_lib.common_sources import gen_list
from dsl.block_lib.sinks.sink_lib.common_sinks import (
    record_to_list,
    record_to_set,
    record_to_file,
    record_to_jsonl,
    record_to_console,
)
from dsl.block_lib.sources.source_lib.common_classes import FromList


def test_sink_direct_values():
    results = []
    network = Network(
        blocks={
            "source": Source(generator_fn=gen_list(["A1", "A2", "__STOP__"])),
            "sink": Sink(record_fn=record_to_list(results))
        },
        connections=[("source", "out", "sink", "in")
                     ]
    )
    network.compile_and_run()
    assert results == ["A1", "A2"]


def test_sink_direct_values_Classes():
    results = []
    network = Network(
        blocks={
            "source": FromList(["A1", "A2", "__STOP__"]),
            "sink": Sink(record_fn=record_to_list(results))
        },
        connections=[("source", "out", "sink", "in")
                     ]
    )
    network.compile_and_run()
    assert results == ["A1", "A2"]

# -------------------------
# In-memory collectors
# -------------------------


def test_record_to_list_direct_values():
    results = []
    network = Network(
        blocks={
            "source": Source(generator_fn=gen_list(["apple", "banana", "__STOP__"])),
            "sink": Sink(record_fn=record_to_list(results))
        },
        connections=[("source", "out", "sink", "in")
                     ]
    )
    network.compile_and_run()
    assert results == ["apple", "banana"]


def test_record_to_list_extract_key_from_dicts():
    results = []
    network = Network(
        blocks={
            "source": Source(generator_fn=gen_list([
                {"fruit": "apple", "color": "red"},
                {"fruit": "banana", "color": "yellow"}
            ])),
            "sink": Sink(record_fn=record_to_list(results, key="fruit"))
        },
        connections=[("source", "out", "sink", "in")]
    )
    network.compile_and_run()
    assert results == ["apple", "banana"]


def test_record_to_set_deduplicates_and_key_1():
    results = set()
    network = Network(
        blocks={
            "source": Source(generator_fn=gen_list([
                "x", "x", "y", "x", "y"])),
            "sink": Sink(record_fn=record_to_set(results))
        },
        connections=[("source", "out", "sink", "in")]
    )
    network.compile_and_run()
    assert results == {"x", "y"}


def test_record_to_set_deduplicates_and_key_2():
    results = set()
    network = Network(
        blocks={
            "source": Source(generator_fn=gen_list([
                {"id": 1, "v": "a"},
                {"id": 1, "v": "b"},
                {"id": 2, "v": "c"}
            ])),
            "sink": Sink(record_fn=record_to_set(results, key="v"))
        },
        connections=[("source", "out", "sink", "in")]
    )
    network.compile_and_run()
    assert results == {"a", "b", "c"}


# -------------------------
# Files (line-by-line, JSONL)
# -------------------------

def test_record_to_file_lines(tmp_path: Path | None = None):
    if tmp_path is None:
        tmp_path = Path(".")

    p = Path(tmp_path) / "out.txt"

    network = Network(
        blocks={
            "source": Source(generator_fn=gen_list(["apple", "banana"])),
            "sink": Sink(record_fn=record_to_file(path=str(p)))
        },
        connections=[("source", "out", "sink", "in")]
    )
    network.compile_and_run()
    text = p.read_text(encoding="utf-8").splitlines()
    assert text == ["apple", "banana"]

    p.unlink(missing_ok=True)


def test_record_to_file_with_key(tmp_path: Path | None = None):
    if tmp_path is None:
        tmp_path = Path(".")

    p = Path(tmp_path) / "names.txt"

    network = Network(
        blocks={
            "source": Source(generator_fn=gen_list([
                {"name": "Ada", "role": "pioneer"},
                {"name": "Grace", "role": "pioneer"}
            ])),
            "sink": Sink(record_fn=record_to_file(path=str(p), key="name"))
        },
        connections=[("source", "out", "sink", "in")]
    )
    network.compile_and_run()

    lines = p.read_text(encoding="utf-8").splitlines()
    assert lines == ["Ada", "Grace"]

    p.unlink(missing_ok=True)


def test_record_to_jsonl_objects(tmp_path: Path | None = None):
    if tmp_path is None:
        tmp_path = Path(".")

    p = Path(tmp_path) / "data.jsonl"

    network = Network(
        blocks={
            "source": Source(generator_fn=gen_list([
                {"k": 1},
                {"k": 2, "nested": {"x": True}}
            ])),
            "sink": Sink(record_fn=record_to_jsonl(str(p)))
        },
        connections=[("source", "out", "sink", "in")]
    )
    network.compile_and_run()
    lines = p.read_text(encoding="utf-8").splitlines()
    objs = [json.loads(line) for line in lines]
    assert objs == [{"k": 1}, {"k": 2, "nested": {"x": True}}]

    p.unlink(missing_ok=True)


def test_record_to_jsonl_with_key(tmp_path: Path | None = None):
    if tmp_path is None:
        tmp_path = Path(".")

    p = Path(tmp_path) / "just_names.jsonl"

    network = Network(
        blocks={
            "source": Source(generator_fn=gen_list([
                {"name": "Ada", "id": 1},
                {"name": "Grace", "id": 2}
            ])),
            "sink": Sink(record_fn=record_to_jsonl(str(p), key="name"))
        },
        connections=[("source", "out", "sink", "in")]
    )
    network.compile_and_run()

    lines = p.read_text(encoding="utf-8").splitlines()
    assert [json.loads(line) for line in lines] == ["Ada", "Grace"]

    p.unlink(missing_ok=True)


# -------------------------
# Console output (manual capture)
# -------------------------

def test_record_to_console_prefix():
    buffer = io.StringIO()
    old_stdout = sys.stdout
    sys.stdout = buffer
    try:
        network = Network(
            blocks={
                "source": Source(generator_fn=gen_list([
                    "apple",
                    "banana"
                ])),
                "sink": Sink(record_fn=record_to_console(prefix=">> "))
            },
            connections=[("source", "out", "sink", "in")]
        )
        network.compile_and_run()
    finally:
        sys.stdout = old_stdout

    captured = buffer.getvalue().splitlines()
    assert captured == [">> apple", ">> banana"]


# -------------------------
# Run as script
# -------------------------

def main():
    # Run all tests manually (basic harness)
    for fn in [
        test_sink_direct_values,
        test_sink_direct_values_Classes,
        test_record_to_list_direct_values,
        test_record_to_list_extract_key_from_dicts,
        test_record_to_set_deduplicates_and_key_1,
        test_record_to_set_deduplicates_and_key_2,
        test_record_to_file_lines,
        test_record_to_file_with_key,
        test_record_to_jsonl_objects,
        test_record_to_jsonl_with_key,
        test_record_to_console_prefix,
    ]:
        fn()
        print(f"{fn.__name__}: PASS")


if __name__ == "__main__":
    main()
