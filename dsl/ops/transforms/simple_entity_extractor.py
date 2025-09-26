# =================================================
#   Simple extractor of countries and people    |
# =================================================
# dsl/block_lib/transformers/transform_lib/simple_entity_extractor.py
from __future__ import annotations
import re
from typing import Any, Dict, List, Set, Tuple

# Minimal demo lists (extend as needed)
COUNTRIES: Set[str] = {
    "United States", "China", "Brazil", "India", "South Africa", "Nepal"
    "UK", "United Kingdom", "Ireland"  # add more
    "Mount Everest",  # treat as place for the example suite
}

# Acronym/alias normalization (lower-cased keys)
COUNTRY_ALIASES: Dict[str, str] = {
    "usa": "United States",
    "us": "United States",
    "u.s.": "United States",
    "uk": "United Kingdom",
    "u.k.": "United Kingdom",
    "England": "United Kingdom"
}

# Match multiword Title Case names (e.g., "South Africa", "Mount Everest")
TITLE_CASE_RE = re.compile(r"\b(?:[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b")
# Match ALL-CAPS acronyms (2–5 letters) possibly with dots (US, U.S., USA)
ACRONYM_RE = re.compile(r"\b(?:[A-Z]{2,5}(?:\.[A-Z]{2,5})?)\b")


def _normalize_country(token: str) -> Tuple[str, str]:
    """
    Return (original, canonical) country string if token maps to a known country.
    - Looks up TITLE CASE tokens directly in COUNTRIES.
    - Maps acronyms/aliases via COUNTRY_ALIASES to canonical name.
    """
    t = token.strip()
    # Direct title-case hit
    if t in COUNTRIES:
        return (t, t)
    # Alias hit (normalize punctuation and case)
    key = t.replace(".", "").lower() if t.isupper() or "." in t else t.lower()
    canon = COUNTRY_ALIASES.get(key)
    if canon and canon in COUNTRIES:
        return (t, canon)
    return (t, "")


def extract_entity(msg: Any, *, canonicalize: bool = False) -> dict:
    """
    Very simple extractor:
      - Finds title-cased spans and ALL-CAPS acronyms.
      - Classifies known countries into 'places'.
      - Everything else that is capitalized goes to 'people & objects'.
    Set canonicalize=True to emit canonical names (e.g., 'United States')
    instead of the original token ('USA').
    """
    out = dict(msg) if isinstance(msg, dict) else {"text": str(msg)}
    text = str(out.get("text", ""))

    # Candidates: title-case spans + acronyms
    candidates = set(TITLE_CASE_RE.findall(
        text)) | set(ACRONYM_RE.findall(text))

    places: List[str] = []
    things: List[str] = []

    print(f"candidates = {candidates}")
    for tok in candidates:
        orig, canon = _normalize_country(tok)
        if canon:
            places.append(canon if canonicalize else orig)
        else:
            # Filter obvious non-entities (year numbers, ‘The’, etc.)
            if tok.isdigit():
                continue
            if tok.lower() in {"the", "and", "of", "in"}:
                continue
            things.append(tok)

    # (Optional) make order stable for tests
    places.sort()
    things.sort()

    out["entities"] = {
        "people": things,
        "places": places,
    }
    return out
