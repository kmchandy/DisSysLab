import json
import pathlib
from typing import Any, Dict, Iterable
from .base import InputConnector


class InputConnectorFile(InputConnector):
    """Reads items from a local JSON file on {"cmd":"pull","args":{"path": "..."}}
       If the JSON is a list → emits each element; if an object → emits once.
    """

    def _pull(self, cmd: str, args: Dict[str, Any]) -> Iterable[Any] | Any:
        path = pathlib.Path(args["path"])
        obj = json.loads(path.read_text(encoding="utf-8"))
        return obj if isinstance(obj, list) else [obj]
