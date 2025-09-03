from __future__ import annotations
from typing import Any, Dict, Iterable, Iterator
from dsl.core import SimpleAgent


class InputConnector(SimpleAgent):
    """
    Base class for *pull-style* inputs (exception-based).

    Ports
    -----
    in   : expects a dict  {"cmd": "pull", "args": {...}}
    out  : sends            {"data": <item>}   for each item returned by `_pull`

    Behavior
    --------
    - Supports only the "pull" command (for now).
    - If the incoming message is malformed or cmd != "pull", raises ValueError/TypeError.
    - Errors from `_pull` are allowed to propagate as exceptions.
      (Your runtime decides whether to stop the network or report nicely.)

    How to extend
    -------------
    Subclasses implement `_pull(self, cmd: str, args: Dict[str, Any])`
    and return EITHER a single item OR an iterable of items.

    Example:
        class InputConnectorFile(InputConnector):
            def _pull(self, cmd, args):
                import json, pathlib
                path = pathlib.Path(args["path"])
                obj = json.loads(path.read_text(encoding="utf-8"))
                return obj if isinstance(obj, list) else [obj]
    """

    def __init__(self, name: str = "InputConnector") -> None:
        # One data outport only.
        super().__init__(name=name, inport="in", outports=["out"],
                         handle_msg=self.handle_msg)

    def handle_msg(self, msg: Dict[str, Any]) -> None:
        """Validate the command and forward each pulled item to out."""
        if not isinstance(msg, dict):
            raise TypeError(
                f"{self.name}: expected dict message, got {type(msg).__name__}")

        cmd = msg.get("cmd")
        if cmd != "pull":
            raise ValueError(
                f"{self.name}: unknown cmd {cmd!r}; only 'pull' is supported")

        args = msg.get("args", {})
        if not isinstance(args, dict):
            raise TypeError(
                f"{self.name}: 'args' must be a dict, got {type(args).__name__}")

        # Delegate: `_pull` may return a single item OR an iterable.
        result = self._pull(cmd, args)

        for item in self._as_items(result):
            self.send({"data": item}, outport="out")

    def _pull(self, cmd: str, args: Dict[str, Any]) -> Iterable[Any] | Any:
        """Subclasses must override. Return one item or many."""
        raise NotImplementedError

    # --- helpers -------------------------------------------------------------

    @staticmethod
    def _as_items(value: Any) -> Iterator[Any]:
        """
        Normalize `value` into an iterator of items.

        Rules:
          - None            -> 0 items
          - str/bytes/dict  -> treat as ONE atomic item (not iterated)
          - general iterable-> iterate it
          - everything else -> treat as ONE item

        Examples:
            _as_items(None)         -> []
            _as_items("hello")      -> ["hello"]   # not ["h","e","l","l","o"]
            _as_items({"a": 1})     -> [{"a": 1}]  # not keys
            _as_items([1,2,3])      -> [1,2,3]
            _as_items(42)           -> [42]
        """
        if value is None:
            return iter(())
        if isinstance(value, (str, bytes, dict)):
            return iter((value,))
        try:
            return iter(value)  # type: ignore[arg-type]
        except TypeError:
            return iter((value,))
