# dsl.ops.transforms.term_frequency.py

from __future__ import annotations
import json
import re
from collections import defaultdict
from typing import Any, Dict, Iterable, List, Mapping, Set, Tuple

# -----------------------------
# Parsing (handles ```json ... ``` and plain JSON strings)
# -----------------------------

_JSON_BLOCK_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)


def parse_agent_messages(messages: Iterable[str]) -> List[Dict[str, Any]]:
    """
    Accepts a list of strings like:
      '```json\\n{ ... }\\n```'  or  '{ ... }'
    Returns a list[dict] (one per JSON object found).
    """
    items: List[Dict[str, Any]] = []
    for entry in messages:
        if not isinstance(entry, str):
            continue
        text = entry.strip()

        # Strip code fences if present
        m = _JSON_BLOCK_RE.search(text)
        if m:
            text = m.group(1)

        # Extract the outermost JSON object
        start, end = text.find("{"), text.rfind("}")
        if start == -1 or end == -1 or end < start:
            continue

        try:
            data = json.loads(text[start: end + 1])
        except json.JSONDecodeError:
            continue

        if isinstance(data, dict):
            items.append(data)
    return items

# -----------------------------
# Key lookup (robust to case/spaces/punct in key names)
# -----------------------------


def _norm_key(k: str) -> str:
    """Normalize a dict key for forgiving matching."""
    return re.sub(r"\W+", "", k.lower())


def get_value_by_key(data: Dict[str, Any], key_name: str) -> Any:
    """
    Case/spacing-insensitive key access:
    returns data[key_name] if present (forgiving), else None.
    """
    target = _norm_key(key_name)
    for k, v in data.items():
        if _norm_key(str(k)) == target:
            return v
    return None

# -----------------------------
# Normalization helpers
# -----------------------------


def _normalize_primary_value(s: str) -> str:
    """Lowercase, strip, remove possessives, collapse spaces/hyphens."""
    s = s.strip().lower()
    s = re.sub(r"[’']", "", s)                # drop apostrophes/possessives
    # non-word -> space (keep hyphens)
    s = re.sub(r"[^\w\s-]+", " ", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def _slug_secondary_term(s: str) -> str:
    """Lowercase + non-word -> underscore for stable term keys."""
    return re.sub(r"\W+", "_", s.strip().lower()).strip("_")


def _to_list_of_strings(x: Any) -> List[str]:
    """Accept list/str/None and return a clean list[str]."""
    if x is None:
        return []
    if isinstance(x, list):
        return [str(y) for y in x if isinstance(y, str) and y.strip()]
    if isinstance(x, str) and x.strip():
        return [x]
    return []

# -----------------------------
# Primary (target) aliasing
# -----------------------------


def _compile_aliases(primary_aliases: Mapping[str, Iterable[str]] | None):
    """
    Compile regex patterns per canonical primary target.
    Example:
      {"JPL": [r"\\bjpl\\b", r"\\bjet propulsion laboratory\\b", ...]}
    """
    if not primary_aliases:
        return {}
    return {
        canon: [re.compile(p, flags=re.IGNORECASE) for p in pats]
        for canon, pats in primary_aliases.items()
    }


def _present_targets_in_doc(
    doc_primary_vals: Iterable[str],
    target_set: Set[str],
    alias_rx: Mapping[str, List[re.Pattern]],
) -> Set[str]:
    """
    Return the set of CANONICAL targets present in the document,
    using alias regex first, then case-insensitive exact match fallback.
    """
    present: Set[str] = set()
    norm_vals = [_normalize_primary_value(
        x) for x in doc_primary_vals if isinstance(x, str)]

    # alias-based matches
    for canon, patterns in alias_rx.items():
        for txt in norm_vals:
            if any(p.search(txt) for p in patterns):
                present.add(canon)
                break

    # exact fallback for any remaining
    remaining = target_set - present
    if remaining:
        vals_set = set(norm_vals)
        for canon in remaining:
            if _normalize_primary_value(canon) in vals_set:
                present.add(canon)

    return present

# -----------------------------
# General-purpose co-occurrence (document frequency)
# -----------------------------


def docfreq_cooccurrence_from_messages(
    messages: Iterable[str],
    *,
    primary_key: str,                   # e.g., "Organizations" or "Company_name"
    # e.g., "Scientific Terms" or "Analyst recommendation"
    secondary_key: str,
    # canonical primary values to count with
    targets: Iterable[str],
    primary_aliases: Mapping[str, Iterable[str]] | None = None,
    slug_secondary_terms: bool = True,  # if True, returns slugified term keys
) -> Dict[str, Dict[str, int]]:
    """
    Compute document-frequency co-occurrence counts of secondary values
    with each target primary value.

    Returns:
      { target: { secondary_value_key: doc_count } }
    """
    items = parse_agent_messages(messages)
    target_set = set(targets)
    alias_rx = _compile_aliases(primary_aliases)

    counts: Dict[str, Dict[str, int]] = {
        t: defaultdict(int) for t in target_set}

    for obj in items:
        prim_val_raw = get_value_by_key(obj, primary_key)
        sec_val_raw = get_value_by_key(obj, secondary_key)

        prim_list = _to_list_of_strings(prim_val_raw)
        sec_list = _to_list_of_strings(sec_val_raw)

        if not prim_list or not sec_list:
            continue

        present_targets = _present_targets_in_doc(
            prim_list, target_set, alias_rx)
        if not present_targets:
            continue

        # de-duplicate secondary values per doc (document frequency)
        if slug_secondary_terms:
            sec_set = {_slug_secondary_term(s) for s in sec_list}
        else:
            # keep raw strings (case-insensitive dedupe)
            sec_set = {s.strip() for s in sec_list}
        sec_set = {s for s in sec_set if s}  # drop empties

        if not sec_set:
            continue

        for t in present_targets:
            for sec in sec_set:
                counts[t][sec] += 1

    # finalize
    return {t: dict(inner) for t, inner in counts.items()}


def top_secondary_for_target(
    counts: Dict[str, Dict[str, int]],
    target: str,
    N: int = 10
) -> List[Tuple[str, int]]:
    """Return Top-N secondary values for a given target by document count."""
    inner = counts.get(target, {})
    return sorted(inner.items(), key=lambda kv: (-kv[1], kv[0]))[:N]
