import json
import pathlib
from typing import Any, Dict, Iterable
from .base import InputConnector


class InputConnectorFile(InputConnector):
    """Reads items from a local JSON file on {"cmd":"pull"}.
       - If file holds a list → emits each element.
       - If file holds an object → emits one item.
    args: {"path": "..."}
    """

    def __init__(self, name: str = "InputConnectorFile") -> None:
        super().__init__(name=name)

    def _pull(self, cmd: str, args: Dict[str, Any]) -> Iterable[Any]:
        path = pathlib.Path(args["path"])
        obj = json.loads(path.read_text(encoding="utf-8"))
        return obj if isinstance(obj, list) else [obj]
