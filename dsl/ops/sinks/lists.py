# dsl/ops/sinks/lists.py
from __future__ import annotations

import json
from typing import Any, Callable, Optional

__all__ = [
    "to_list",
    "to_set",
    "to_file",
    "to_jsonl",
    "to_console",
]


def _maybe_extract(msg: Any, key: Optional[str]) -> Any:
    if key is None:
        return msg
    if isinstance(msg, dict):
        return msg[key]  # raise KeyError if missing to surface errors early
    raise TypeError(
        f"record_* with key='{key}' expects dict messages, got {type(msg).__name__}")


def to_list(msg, target: list, key: Optional[str] = None) -> Callable[[Any], None]:
    """
    Append each message to `target`. If key is provided, append msg[key].
    """
    target.append(msg if key is None else msg[key])


def to_set(msg, target_set: set, key: Optional[str] = None) -> Callable[[Any, Any], None]:
    target_set.add(_maybe_extract(msg, key))


def to_file(msg, path: str, key: Optional[str] = None) -> Callable[[Any, Any], None]:
    val = _maybe_extract(msg, key)
    with open(path, "a", encoding="utf-8") as f:
        f.write(f"{val}\n")


def to_jsonl(msg, path: str, key: Optional[str] = None) -> Callable[[Any, Any], None]:
    val = _maybe_extract(msg, key)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(val, ensure_ascii=False) + "\n")


def to_console(prefix: str = "") -> Callable[[Any, Any], None]:
    print(f"{prefix}{msg}")
