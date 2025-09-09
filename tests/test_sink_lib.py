# tests/test_sink_lib.py
from __future__ import annotations

import json
import sys
import io
from pathlib import Path

from dsl.block_lib.sinks.sink_lib import (
    record_to_list,
    record_to_set,
    record_to_file,
    record_to_jsonl,
    record_to_console,
)


class DummyAgent:
    """Minimal stub in case a sink uses agent.name etc."""

    def __init__(self, name: str = "Dummy"):
        self.name = name


# -------------------------
# In-memory collectors
# -------------------------

def test_record_to_list_direct_values():
    out = []
    fn = record_to_list(out)

    agent = DummyAgent()
    fn(agent, "apple")
    fn(agent, "banana")

    assert out == ["apple", "banana"]


def test_record_to_list_extract_key_from_dicts():
    out = []
    fn = record_to_list(out, key="fruit")

    agent = DummyAgent()
    fn(agent, {"fruit": "apple", "color": "red"})
    fn(agent, {"fruit": "banana", "color": "yellow"})

    assert out == ["apple", "banana"]


def test_record_to_set_deduplicates_and_key():
    out = set()
    fn = record_to_set(out)

    agent = DummyAgent()
    fn(agent, "x")
    fn(agent, "x")
    fn(agent, "y")
    assert out == {"x", "y"}

    out2 = set()
    fn2 = record_to_set(out2, key="id")
    fn2(agent, {"id": 1, "v": "a"})
    fn2(agent, {"id": 1, "v": "b"})
    fn2(agent, {"id": 2, "v": "c"})
    assert out2 == {1, 2}


# -------------------------
# Files (line-by-line, JSONL)
# -------------------------

def test_record_to_file_lines(tmp_path: Path | None = None):
    if tmp_path is None:
        tmp_path = Path(".")

    p = Path(tmp_path) / "out.txt"
    fn = record_to_file(str(p))

    agent = DummyAgent()
    fn(agent, "apple")
    fn(agent, "banana")

    text = p.read_text(encoding="utf-8").splitlines()
    assert text == ["apple", "banana"]

    p.unlink(missing_ok=True)


def test_record_to_file_with_key(tmp_path: Path | None = None):
    if tmp_path is None:
        tmp_path = Path(".")

    p = Path(tmp_path) / "names.txt"
    fn = record_to_file(str(p), key="name")

    agent = DummyAgent()
    fn(agent, {"name": "Ada", "role": "pioneer"})
    fn(agent, {"name": "Grace", "role": "pioneer"})

    lines = p.read_text(encoding="utf-8").splitlines()
    assert lines == ["Ada", "Grace"]

    p.unlink(missing_ok=True)


def test_record_to_jsonl_objects(tmp_path: Path | None = None):
    if tmp_path is None:
        tmp_path = Path(".")

    p = Path(tmp_path) / "data.jsonl"
    fn = record_to_jsonl(str(p))

    agent = DummyAgent()
    fn(agent, {"k": 1})
    fn(agent, {"k": 2, "nested": {"x": True}})

    lines = p.read_text(encoding="utf-8").splitlines()
    objs = [json.loads(line) for line in lines]
    assert objs == [{"k": 1}, {"k": 2, "nested": {"x": True}}]

    p.unlink(missing_ok=True)


def test_record_to_jsonl_with_key(tmp_path: Path | None = None):
    if tmp_path is None:
        tmp_path = Path(".")

    p = Path(tmp_path) / "just_names.jsonl"
    fn = record_to_jsonl(str(p), key="name")

    agent = DummyAgent()
    fn(agent, {"name": "Ada", "id": 1})
    fn(agent, {"name": "Grace", "id": 2})

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
        fn = record_to_console(prefix=">> ")
        agent = DummyAgent()
        fn(agent, "apple")
        fn(agent, "banana")
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
        test_record_to_list_direct_values,
        test_record_to_list_extract_key_from_dicts,
        test_record_to_set_deduplicates_and_key,
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
