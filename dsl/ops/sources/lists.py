# dsl/ops/sources/lists.py
from __future__ import annotations
import time
from datetime import datetime
from typing import Any, Iterable, Iterator, Optional, Callable

__all__ = [
    "from_list",
    "from_list_with_delay",
    "from_list_with_key",
    "from_list_with_key_with_time",
]


def _now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def from_list(items: Iterable[Any]) -> Iterator[Any]:
    for item in items:
        yield item


def from_list_with_delay(items: Iterable[Any], delay: Optional[float] = None) -> Iterator[Any]:
    for x in items:
        yield x
        if delay:
            time.sleep(delay)


def from_list_with_key(items: Iterable[Any], key: str) -> Iterator[dict]:
    for x in items:
        yield {key: x}


def from_list_with_key_with_time(
    items: Iterable[Any],
    key: str,
    time_key: str = "time",
    now: Callable[[], str] = _now_str,
) -> Iterator[dict]:
    for x in items:
        yield {key: x, time_key: now()}
