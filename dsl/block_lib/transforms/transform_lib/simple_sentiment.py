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
    "great", "excellent", "superb", "fantastic", "positive",
    "best", "strongest", "high", "higher", "highest",
    "soar", "soars", "rally", "strong", "boost", "rise", "rises", "up",
    "improve", "improves", "improved", "lead", "leads", "leading",
}
NEGATIVE_WORDS = {
    "loss", "losses", "fall", "falls", "fell", "drop", "drops", "down",
    "bad", "terrible", "horrible", "negative", "poor",
    "worst", "weakest", "low", "lower", "lowest",
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


def add_sentiment(
    msg: Any,
    *,
    input_key: str = "text",
    add_key: str = "sentiment",
    positive_words: Optional[Iterable[str]] = None,
    negative_words: Optional[Iterable[str]] = None,
) -> dict:

    if not isinstance(msg, dict):
        raise ValueError("Input message to AddSentiment must be a dict")
    print(f"msg: {msg}")
    text = msg[input_key]
    if not isinstance(text, str):
        raise ValueError(
            "The text field of an input message to AddSentiment must be a string")
    score = sentiment_score(text, positive_words, negative_words)
    return {input_key: text, add_key: label_from_score(score)}
