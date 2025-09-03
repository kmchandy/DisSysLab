from __future__ import annotations
from typing import Any, Dict, List
from dsl.core import SimpleAgent


class OutputConnector(SimpleAgent):
    """
    Base class for *flush-style* outputs.
    Subclasses must implement `_flush(payload, meta)`.
    Has a single inport "in" that accepts flush commands.
    Has no outports.

    Messages on input port "in" must be dict of the following format:
    -----
    {"cmd": "flush", "payload": [...], "meta": {...}}
         - payload : list[Any]   (items to write)
         - meta    : dict        (destination/config info)

    Behavior
    --------
    - Supports only the "flush" command. More commands may be added later.
    - Validates types and raises TypeError/ValueError on bad input.
    - Calls subclass `_flush(payload, meta)` to perform the write.

    How to extend
    -------------
    Subclass and implement:
        _flush(self, payload: List[Any], meta: Dict[str, Any]) -> None

    Example:
        class OutputConnectorFileMarkdown(OutputConnector):
            def _flush(self, payload, meta):
                import pathlib
                path = pathlib.Path(meta["path"])
                title = meta.get("title", "Report")
                lines = [f"# {title}", ""]
                for item in payload:
                    if isinstance(item, dict) and "row" in item:
                        lines.append(item["row"])
                    else:
                        lines.append(f"- {item}")
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("\\n".join(lines), encoding="utf-8")
    """

    def __init__(self, name: str = "OutputConnector") -> None:
        # No data outports needed; this block performs a side-effect (writing).
        super().__init__(name=name, inport="in", outports=[], handle_msg=self.handle_msg)

    def handle_msg(self, msg: Dict[str, Any]) -> None:
        """Validate the command and perform a single flush."""
        if not isinstance(msg, dict):
            raise TypeError(
                f"{self.name}: expected dict message, got {type(msg).__name__}")

        cmd = msg.get("cmd")
        if cmd != "flush":
            raise ValueError(
                f"{self.name}: unknown cmd {cmd!r}; only 'flush' is supported")

        payload = msg.get("payload")
        meta = msg.get("meta", {})

        if not isinstance(payload, list):
            raise TypeError(
                f"{self.name}: 'payload' must be a list, got {type(payload).__name__}")
        if not isinstance(meta, dict):
            raise TypeError(
                f"{self.name}: 'meta' must be a dict, got {type(meta).__name__}")

        # Delegate: subclass performs the actual write by overloading _flush()
        self._flush(payload, meta)

    # --- to be implemented by subclasses ------------------------------------

    def _flush(self, payload: List[Any], meta: Dict[str, Any]) -> None:
        """Subclasses must override: perform one write operation."""
        raise NotImplementedError
