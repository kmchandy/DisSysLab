# add near the top
from dsl.block_lib.sinks.sink import Sink
from dsl.block_lib.sinks.sink_lib.common_sinks import (
    record_to_list,
    record_to_set,
    record_to_file,
    record_to_jsonl,
    record_to_console,
)
from typing import Optional

# extend the public API
__all__ = ["ToList", "ToSet", "ToFile", "ToJSONL", "ToConsole"]


class ToList(Sink):
    """Append each message to a Python list (optionally msg[key])."""

    def __init__(self, target: list, key: Optional[str] = None, name: str = "ToList"):
        super().__init__(name=name, record_fn=record_to_list(target, key))


class ToSet(Sink):
    """Add each message to a Python set (optionally msg[key])."""

    def __init__(self, target_set: set, key: Optional[str] = None, name: str = "ToSet"):
        super().__init__(name=name, record_fn=record_to_set(target_set, key))


class ToFile(Sink):
    """Append one line per message to a text file (optionally msg[key])."""

    def __init__(self, path: str, key: Optional[str] = None, name: str = "ToFile"):
        super().__init__(name=name, record_fn=record_to_file(path, key))


class ToJSONL(Sink):
    """Append one JSON object per line to a .jsonl file (optionally msg[key])."""

    def __init__(self, path: str, key: Optional[str] = None, name: str = "ToJSONL"):
        super().__init__(name=name, record_fn=record_to_jsonl(path, key))


class ToConsole(Sink):
    """Print each message to stdout with an optional prefix."""

    def __init__(self, prefix: str = "", name: str = "ToConsole"):
        super().__init__(name=name, record_fn=record_to_console(prefix))
