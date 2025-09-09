# dsl/block_lib/transformers/transform_lib/simple_sentiment.py
from __future__ import annotations
import re
from typing import Any, Optional, Iterable, Dict


# ---------------------------------------------------------------------
# Simple sentiment analysis functions and keyword lists.
# ---------------------------------------------------------------------
__all__ = [
    "POSITIVE_WORDS",
    "NEGATIVE_WORDS",
    "tokenize_words",
    "sentiment_score",
    "label_from_score",
    "add_sentiment",
]

# Keyword lists kept simple for pedagogy.
POSITIVE_WORDS = {
    "win", "wins", "won", "surge", "record", "growth", "beat", "beats",
    "soar", "soars", "rally", "strong", "boost", "rise", "rises", "up",
    "improve", "improves", "improved", "lead", "leads", "leading",
}
NEGATIVE_WORDS = {
    "loss", "losses", "fall", "falls", "fell", "drop", "drops", "down",
    "injury", "injuries", "fear", "fears", "concern", "concerns",
    "weak", "decline", "declines", "miss", "misses", "missed",
    "slump", "slumps", "plunge", "plunges",
}

_word_re = re.compile(r"[A-Za-z']+")


def tokenize_words(text: str) -> list[str]:
    """Simple word tokenizer that avoids substring false-positives (e.g., 'miss' vs 'mission')."""
    return [w.casefold() for w in _word_re.findall(text)]


def sentiment_score(
    text: str,
    positive_words: Optional[Iterable[str]] = None,
    negative_words: Optional[Iterable[str]] = None,
) -> int:
    """Return integer score: (#positives) - (#negatives)."""
    pos = set(POSITIVE_WORDS if positive_words is None else positive_words)
    neg = set(NEGATIVE_WORDS if negative_words is None else negative_words)
    words = tokenize_words(text)
    pos_hits = sum(1 for w in words if w in pos)
    neg_hits = sum(1 for w in words if w in neg)
    return pos_hits - neg_hits


def label_from_score(score: int) -> str:
    if score > 0:
        return "Positive"
    if score < 0:
        return "Negative"
    return "Neutral"


def _coerce_to_dict(msg: Any, text_key: str) -> Dict[str, Any]:
    if isinstance(msg, dict):
        return dict(msg)  # return a COPY; don't mutate input
    return {text_key: str(msg)}


def add_sentiment(
    msg: Any,
    *,
    text_key: str = "text",
    out_key: str = "sentiment",
    include_counts: bool = False,
    positive_words: Optional[Iterable[str]] = None,
    negative_words: Optional[Iterable[str]] = None,
) -> dict:
    """
    Pure mapping: returns a NEW dict with {out_key: "Positive|Negative|Neutral"}.
    - If msg is not a dict, it is coerced to {text_key: str(msg)}.
    - If msg is a dict, it is shallow-copied and annotated.
    """
    out = _coerce_to_dict(msg, text_key=text_key)
    text = str(out.get(text_key, ""))
    score = sentiment_score(text, positive_words, negative_words)
    out[out_key] = label_from_score(score)
    if include_counts:
        # Optional extras for teaching/demos
        words = tokenize_words(text)
        pos = set(POSITIVE_WORDS if positive_words is None else positive_words)
        neg = set(NEGATIVE_WORDS if negative_words is None else negative_words)
        out["sentiment_score"] = score
        out["pos_count"] = sum(1 for w in words if w in pos)
        out["neg_count"] = sum(1 for w in words if w in neg)
    return out
