from __future__ import annotations
from typing import Any, Dict, Iterable, Iterator
import csv
import pathlib
from .base import InputConnector


class InputConnectorCSV(InputConnector):
    """
    Pulls CSV rows as dicts.

    Message to 'in':
        {"cmd":"pull","args":{"path":"...", "encoding":"utf-8"}}

    Emits on 'out':
        {"data": {"colA":"...", "colB":"..."}}
    """

    def _pull(self, cmd: str, args: Dict[str, Any]) -> Iterable[Dict[str, Any]] | Any:
        path = pathlib.Path(args["path"])
        enc = args.get("encoding", "utf-8")
        with path.open("r", newline="", encoding=enc) as f:
            reader = csv.DictReader(f)
            for row in reader:
                yield dict(row)
