import os
import re
import csv
from typing import Dict, Any, Iterable, List, Tuple
from collections import defaultdict

# ---------------------------
# Pretty + grouping helpers
# ---------------------------

TOP_K = 10           # show at most this many tokens per batch
MIN_COUNT = 1        # drop terms below this doc-count
QUOTE_ALL = True     # quote every cell for safety

# Simple substring-based families -> canonical label
GROUPS = {
    # gravitational, gravity, gravimeter...
    "gravity":        ["gravit"],
    # careful: include if you want "moon" grouped
    "lunar":          ["lunar", "moon"],
    "solar":          ["solar", "sunspot", "sun"],
    "exoplanet":      ["exoplan", "exo-planet"],
    "interferometer": ["interferometer"],
    "aurora":         ["aurora"],
    "artemis":        ["artemis"]
    # add/trim freely for your dataset
}


def _slug(s: str) -> str:
    return re.sub(r"\W+", "_", s.strip().lower()).strip("_")


def _pretty(s: str) -> str:
    # title-case words, preserve ALLCAPS tokens like JWST
    words = s.replace("_", " ").split()

    def fix(w: str) -> str:
        return w if (len(w) > 1 and w.isupper()) else w.capitalize()
    return " ".join(fix(w) for w in words)


def _slug_filename(name: str) -> str:
    s = str(name).strip().lower()
    s = re.sub(r"[^\w\-]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s or "org"


def _group_counts(term_counts: Dict[str, Any],
                  groups: Dict[str, Iterable[str]],
                  min_count: int) -> Dict[str, int]:
    """
    Collapse raw terms into families using substring rules on slugs.
    Unmatched terms keep their own (slug) label.
    """
    out: Dict[str, int] = defaultdict(int)
    for term, cnt in term_counts.items():
        try:
            n = int(cnt)
        except Exception:
            continue
        if n < min_count:
            continue
        slug = _slug(str(term))
        label = None
        for canon, pats in groups.items():
            # First matching family wins
            if any(p in slug for p in pats):
                label = canon
                break
        out[label or slug] += n
    return dict(out)


def _format_paired(items: List[Tuple[str, int]]) -> List[str]:
    """term(count) tokens with pretty labels."""
    return [f"{_pretty(t)}({n})" for t, n in items]

# ---------------------------
# Sink: one pretty line per batch, per org
# ---------------------------


def write_batch_per_org_csv(
    message: Dict[str, Dict[str, Any]],   # {org: {term: count}}
    out_dir: str = "counts_csv",
    *,
    top_k: int = TOP_K,
    min_count: int = MIN_COUNT,
    groups: Dict[str, Iterable[str]] = GROUPS,
    quote_all: bool = QUOTE_ALL,
) -> None:
    if not isinstance(message, dict):
        raise TypeError("message must be a dict {org: {term: count}}")

    os.makedirs(out_dir, exist_ok=True)

    for org, term_counts in message.items():
        if not isinstance(term_counts, dict):
            continue

        # 1) group + filter
        grouped = _group_counts(term_counts, groups, min_count)

        # 2) sort by decreasing count, then lexicographically
        items = sorted(grouped.items(), key=lambda kv: (-kv[1], kv[0]))[:top_k]

        # 3) format as "Term(count)" tokens
        row = _format_paired(items) if items else []

        # 4) append one line to the org's CSV
        path = os.path.join(out_dir, f"{_slug_filename(org)}.csv")
        with open(path, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(
                f, quoting=csv.QUOTE_ALL if quote_all else csv.QUOTE_MINIMAL)
            writer.writerow(row)
