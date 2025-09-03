from __future__ import annotations
from typing import Any, Dict, Iterable
import requests

from .base import InputConnector  # inherits your exception-based SimpleAgent


class InputConnectorHTTPJSON(InputConnector):
    """
    Pull JSON from a public HTTP endpoint (no auth).

    Command:
        {"cmd": "pull", "args": {"url": "...", "method": "GET", "params": {...}, "headers": {...}}}

    Behavior:
    - Parses JSON via response.json()
    - If the JSON is a list → emits each element as an item
    - If it's an object → emits that single object
    """

    def __init__(self, name: str = "InputConnectorHTTPJSON") -> None:
        super().__init__(name=name)

    def _pull(self, cmd: str, args: Dict[str, Any]) -> Iterable[Any] | Any:
        url = args.get("url")
        if not url or not isinstance(url, str):
            raise ValueError(f"{self.name}: 'url' (str) is required")

        method = (args.get("method") or "GET").upper()
        params = args.get("params") or {}
        headers = args.get("headers") or {}

        resp = requests.request(
            method, url, params=params, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        # Return either a list (iterable) or a single object
        return data
