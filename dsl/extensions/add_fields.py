# dsl/extensions/add_fields.py
from typing import Any, Callable, Dict, Optional
import json
import re


def _parse_jsonish(s: str) -> Optional[dict]:
    """
    Best-effort parser for strings that *should* contain a JSON object.
    Strategy (in order):
      1) Direct json.loads(s)
      2) Strip a leading "name = " style prefix and json.loads(...)
      3) Find the *last* non-greedy {...} block and json.loads(...) that block
    Returns a dict on success, else None.
    """
    # 1) direct
    try:
        return json.loads(s)
    except Exception:
        pass

    # 2) strip leading "name = " prefix (e.g., "topics = {...}")
    s2 = re.sub(r"^\s*[\w\-]+\s*=\s*", "", s, count=1)
    if s2 != s:  # <-- use equality, not identity
        try:
            return json.loads(s2)
        except Exception:
            pass

    # 3) grab the *last* non-greedy {...} block (reduces over-capture)
    last_match = None
    for m in re.finditer(r"\{.*?\}", s, flags=re.DOTALL):
        last_match = m
    if last_match:
        try:
            return json.loads(last_match.group(0))
        except Exception:
            return None

    return None


def _is_empty(value: Any) -> bool:
    """
    Generic emptiness:
      - None -> empty
      - str  -> empty if whitespace-only
      - dict -> empty if all values empty (recursive)
      - list/tuple/set -> empty if len==0 or all items empty (recursive)
      - bytes/bytearray -> empty if len==0
      - numbers/bools/others -> treated as non-empty by default
    """
    if value is None:
        return True
    if isinstance(value, str):
        return len(value.strip()) == 0
    if isinstance(value, dict):
        return all(_is_empty(v) for v in value.values())
    if isinstance(value, (list, tuple, set)):
        return len(value) == 0 or all(_is_empty(v) for v in value)
    if isinstance(value, (bytes, bytearray)):
        return len(value) == 0
    return False


def add_fields(
    msg: Dict[str, Any],
    key: str,
    fn: Callable[[str], Any],
    drop_msg: bool = False,
    drop_fn: Callable[[Any], bool] = _is_empty,
) -> Optional[Dict[str, Any]]:
    """
    Run an agent over msg[key]. The agent may return a JSON string or a structured object.

    Flow:
      - Read msg[key] as text; if empty/whitespace:
          * return None if drop_msg=True (default),
          * else return the original msg unchanged.
      - Call fn(text) -> raw
      - If raw is a string, attempt to parse to dict via _parse_jsonish(); if already a dict, use it; else:
          * return None if drop_msg=True,
          * else return the original msg unchanged.
      - Apply drop_fn(dict). If it returns True (e.g., dict has no non-empty values):
          * return None if drop_msg=True,
          * else return the original msg unchanged.
      - Otherwise, merge dict into msg (last-writer-wins) and return msg.

    Notes:
      - With drop_msg=True this acts as a filter (may return None).
      - With drop_msg=False this acts as a pass-through enricher: on failure it leaves msg unchanged.
      - Merging uses msg.update(data) and can overwrite existing keys by design.
    """
    text = (msg.get(key) or "").strip()
    if not text:
        return None if drop_msg else msg

    try:
        raw = fn(text)
    except Exception:
        return None if drop_msg else msg

    # Normalize to dict
    if isinstance(raw, str):
        data = _parse_jsonish(raw)
    elif isinstance(raw, dict):
        data = raw
    else:
        data = None

    if not isinstance(data, dict):
        return None if drop_msg else msg

    # Generic emptiness check
    if drop_fn(data):
        return None if drop_msg else msg

    # Merge and pass through
    msg.update(data)  # last-writer-wins; be mindful of key collisions
    return msg


__all__ = ["add_fields", "_parse_jsonish", "_is_empty"]
