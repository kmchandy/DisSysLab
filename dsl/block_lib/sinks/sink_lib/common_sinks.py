# dsl/block_lib/sinks/sink_lib.py
from __future__ import annotations

import json
from typing import Any, Callable, Optional

__all__ = [
    "record_to_list",
    "record_to_set",
    "record_to_file",
    "record_to_jsonl",
    "record_to_console",
]


def _maybe_extract(msg: Any, key: Optional[str]) -> Any:
    if key is None:
        return msg
    if isinstance(msg, dict):
        return msg[key]  # raise KeyError if missing to surface errors early
    raise TypeError(
        f"record_* with key='{key}' expects dict messages, got {type(msg).__name__}")


def record_to_list(target: list, key: Optional[str] = None) -> Callable[[Any], None]:
    """
    Append each message to `target`. If key is provided, append msg[key].
    """
    def _fn(msg: Any) -> None:
        target.append(msg if key is None else msg[key])
    return _fn


def record_to_set(target_set: set, key: Optional[str] = None) -> Callable[[Any, Any], None]:
    def _fn(msg):
        target_set.add(_maybe_extract(msg, key))
    return _fn


def record_to_file(path: str, key: Optional[str] = None) -> Callable[[Any, Any], None]:
    def _fn(msg):
        val = _maybe_extract(msg, key)
        with open(path, "a", encoding="utf-8") as f:
            f.write(f"{val}\n")
    return _fn


def record_to_jsonl(path: str, key: Optional[str] = None) -> Callable[[Any, Any], None]:
    def _fn(msg):
        val = _maybe_extract(msg, key)
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(val, ensure_ascii=False) + "\n")
    return _fn


def record_to_console(prefix: str = "") -> Callable[[Any, Any], None]:
    def _fn(msg):
        print(f"{prefix}{msg}")
    return _fn
