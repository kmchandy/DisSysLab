# dsl.connectors.jetstream_filter.py
from __future__ import annotations
import re
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set


class Jetstream_Filter:
    """
    Lightweight preprocessor for Bluesky posts (Jetstream events).
    Applies hygiene filters, optional topic gating, simple sampling,
    and (optionally) normalizes fields for an LLM node.

    Parameters
    ----------
    min_len : int, default 15
        Minimum number of characters a post must have to be kept.
        (Whitespace-trimmed length.)
    max_len : int, default 800
        Maximum number of characters a post may have to be kept.
    require_langs : Sequence[str] | None, default ('en',)
        Language allow-list. If the incoming message has a non-empty
        `lang` list, the post is kept only if there is an intersection
        with `require_langs`. If the message has no `lang` info at all,
        it is **not** filtered by language. Set to None to disable lang checks.
    allow_topics : Iterable[str] | None, default None
        Optional hashtag allow-list used to gate posts by topic.
        Provide raw names without '#', e.g. {'nasa','ai','python'}.
        When set, a post is kept only if it contains at least one
        of these hashtags (case-insensitive). If None, no topic gate.
    sample_every_n : int | None, default None
        Down-sampling rate. If set to N ≥ 2, keeps every Nth post and drops
        the rest (helps classroom readability). If None or N <= 1, keeps all.
    hashtag_pattern : str, default r"(?:^|\\s)#(\\w{2,50})\\b"
        Regex used to extract hashtag tokens from text. Must contain one
        capturing group for the hashtag (without '#').
    add_llm_fields : bool, default True
        If True, adds fields expected by your LLM extractor:
          - 'title' := ""  (empty string placeholder)
          - 'page_text' := post text
    add_timestamp_alias : bool, default True
        If True, sets 'ts' := msg['created_at'] (pass-through alias).

    Notes
    -----
    • Input message is expected to look like what Jetstream_In emits:
      {'text': str, 'created_at': iso8601, 'lang': [..]?, ...}
    • This transform returns either a new dict (kept) or None (dropped).
    • Hashtags are extracted from the post text using regex and attached
      as a lowercased, sorted list under 'hashtags'.

    Examples
    --------
    >>> f = BlueskyStreamFilter(min_len=20, allow_topics={'nasa','ai'}, sample_every_n=3)
    >>> out = f({'text': 'Loving #NASA images!', 'lang': ['en'], 'created_at':'2025-10-06T01:02:03Z'})
    >>> out is None  # too short -> dropped
    True
    """

    def __init__(
        self,
        *,
        name: str | None = None,
        min_len: int = 15,
        max_len: int = 800,
        require_langs: Optional[Sequence[str]] = ("en",),
        sample_every_n: Optional[int] = None,
    ) -> None:
        self._name = name or self.__class__.__name__
        self.min_len = int(min_len)
        self.max_len = int(max_len)
        self.require_langs = tuple(
            require_langs) if require_langs is not None else None
        self.sample_every_n = int(sample_every_n or 0)
        # internal counter for sampling
        self._i = 0

    @property
    def __name__(self) -> str:  # for frameworks that read fn.__name__
        return self._name

    def __call__(self, msg: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Sample stream and eliminate posts that are too short or too long
        and in languages other than that specified.
        Returns a new dict .
        """
        # 0) Sample every n posts.
        self._i += 1
        if self.sample_every_n and self.sample_every_n > 1:
            if (self._i % self.sample_every_n) != 0:
                return None

        # 1) Basic shape / text
        text = (msg.get("text") or "").strip()
        if not text:
            return None

        # 2) Language allow-list (only if lang info present)
        if self.require_langs is not None:
            langs = msg.get("lang") or []
            if langs:  # only enforce if the message actually carries hints
                if not any(l in self.require_langs for l in langs):
                    return None

        # 3) Length bounds
        n = len(text)
        if n < self.min_len or n > self.max_len:
            return None

        # 4) Build output
        out = dict(msg)
        out["page_text"] = text    # ...and "page_text"
        print(f"In Jetstream_Filter out = {out}")
        return out

    def run(self):
        """alias for __call__."""
        return self.__call__()
