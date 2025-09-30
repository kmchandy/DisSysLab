# dsl/ops/sources/__init__.py
"""
Exports:
- read_lines, get_text, parse
- from_file_lines, from_jsonl, from_http_text, from_http_json

Design:
- Connectors live under dsl/connectors/*. They are the canonical implementations.
- Here we:
  • Re-export connector helpers for convenience/discoverability.
  • Provide Source-shaped wrappers for Graph (fn(**params) -> Iterator).
"""

from __future__ import annotations

from typing import Iterator, Any

# Low-level connectors (canonical)
from dsl.connectors.file_system import read_lines as _read_lines, read_jsonl as _read_jsonl
from dsl.connectors.http import get_text as _get_text, get_json as _get_json
from dsl.connectors.rss import parse as _parse

# -------- Re-export connector helpers (so students can import them here) --------
read_lines = _read_lines
get_text = _get_text
parse = _parse

# -------- Source-shaped wrappers (v2: fn(**params) -> Iterator) --------


def from_file_lines(*, path: str, encoding: str = "utf-8", strip_newline: bool = True) -> Iterator[str]:
    """Source: yield lines from a text file (wraps connectors.file_system.read_lines)."""
    yield from _read_lines(path, encoding=encoding, strip_newline=strip_newline)


def from_jsonl(*, path: str, encoding: str = "utf-8") -> Iterator[Any]:
    """Source: yield JSON objects from a .jsonl file (wraps connectors.file_system.read_jsonl)."""
    yield from _read_jsonl(path, encoding=encoding)


def from_http_text(*, url: str, timeout: float = 10.0) -> Iterator[str]:
    """Source: yield the response body as a single string (wraps connectors.http.get_text)."""
    yield _get_text(url, timeout=timeout)


def from_http_json(*, url: str, timeout: float = 10.0) -> Iterator[Any]:
    """Source: yield parsed JSON as a single message (wraps connectors.http.get_json)."""
    yield _get_json(url, timeout=timeout)


__all__ = [
    # connector helpers
    "read_lines", "get_text", "parse",
    # sources
    "from_file_lines", "from_jsonl", "from_http_text", "from_http_json",
]
