# dsl/connectors/file_system.py
from __future__ import annotations

from pathlib import Path
from typing import Iterator, Any
import json


def read_lines(
    path: str | Path,
    *,
    encoding: str = "utf-8",
    strip_newline: bool = True,
) -> Iterator[str]:
    """
    Yield lines from a text file.

    If strip_newline=True, trailing '\n' is removed per line.
    """
    p = Path(path)
    with p.open("r", encoding=encoding) as f:
        for line in f:
            yield line.rstrip("\n") if strip_newline else line


def write_line(
    path: str | Path,
    line: str,
    *,
    encoding: str = "utf-8",
    append: bool = True,
) -> None:
    """
    Append (or overwrite) a single text line. Ensures a trailing newline.
    """
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    mode = "a" if append else "w"
    with p.open(mode, encoding=encoding) as f:
        f.write(line)
        if not line.endswith("\n"):
            f.write("\n")


def read_jsonl(
    path: str | Path,
    *,
    encoding: str = "utf-8",
) -> Iterator[Any]:
    """
    Yield JSON objects from a .jsonl file (one JSON object per line).
    """
    for line in read_lines(path, encoding=encoding, strip_newline=True):
        if not line:
            continue
        yield json.loads(line)


def write_jsonl(
    path: str | Path,
    obj: Any,
    *,
    encoding: str = "utf-8",
    append: bool = True,
) -> None:
    """
    Append a single JSON object as one line to a .jsonl file.
    """
    write_line(path, json.dumps(obj, ensure_ascii=False),
               encoding=encoding, append=append)
