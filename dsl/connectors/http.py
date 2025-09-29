# dsl/connectors/http.py
from __future__ import annotations

from typing import Any, Dict, Optional
import json
import urllib.request

_DEFAULT_HEADERS: Dict[str, str] = {"User-Agent": "DisSysLab/1.0"}


def get_text(
    url: str,
    *,
    timeout: float = 10.0,
    headers: Optional[Dict[str, str]] = None,
    encoding: Optional[str] = None,
) -> str:
    """
    Fetch text from URL using stdlib urllib.
    Encoding is chosen from the response when possible, else utf-8.
    """
    req = urllib.request.Request(url, headers=headers or _DEFAULT_HEADERS)
    # nosec B310 (teaching code)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = r.read()
        enc = encoding or (r.headers.get_content_charset() or "utf-8")
    return data.decode(enc, errors="replace")


def get_json(url: str, **kwargs) -> Any:
    """
    Fetch JSON from URL and parse into a Python object.
    """
    return json.loads(get_text(url, **kwargs))
