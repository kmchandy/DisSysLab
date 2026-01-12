# dsl.connectors.filter_post
import re
from typing import Any, Dict, Optional


class FilterPost:
    """
    Drops a post (returns None) if:
      • 'lang' exists and doesn't include 'en' (case-insensitive)
      • missing/non-string text
      • text too short after whitespace collapse (min_len)
      • text is only URLs/mentions/emojis/hashtags (if drop_noise_only=True)
      • text contains non-English charset chars (if enforce_english_charset=True)

    Otherwise, collapses whitespace, truncates to max_len, writes back to post["text"],
    and returns the post.
    """

    # Precompiled detectors
    URL_RE = re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE)
    MENTION_RE = re.compile(r"(?<!\w)@\w{1,50}\b")
    HASHTAG_RE = re.compile(r"(?<!\w)#\w{2,50}\b")
    EMOJI_RE = re.compile(
        "["                                  # common emoji/symbol blocks
        "\U0001F1E0-\U0001F1FF"              # flags
        "\U0001F300-\U0001F5FF"              # symbols & pictographs
        "\U0001F600-\U0001F64F"              # emoticons
        "\U0001F680-\U0001F6FF"              # transport & map
        "\U0001F700-\U0001F77F"
        "\U0001F780-\U0001F7FF"
        "\U0001F800-\U0001F8FF"
        "\U0001F900-\U0001F9FF"
        "\U0001FA00-\U0001FAFF"
        "\u2600-\u26FF"                      # misc symbols
        "\u2700-\u27BF"                      # dingbats
        "]",
        flags=re.UNICODE,
    )

    def __init__(
        self,
        *,
        min_len: int = 20,
        max_len: int = 2000,
        enforce_english_charset: bool = True,
        drop_noise_only: bool = True,
        allowed_extras: str = "’‘“”–—…",  # common publishing marks
    ) -> None:
        self.min_len = int(min_len)
        self.max_len = int(max_len)
        self.enforce_english_charset = bool(enforce_english_charset)
        self.drop_noise_only = bool(drop_noise_only)
        self.allowed_extras = allowed_extras

    def run(self, post: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        # 1) Language gate (only if 'lang' present)
        langs = post.get("lang") or []
        if isinstance(langs, str):
            langs = [langs]
        langs_lc = {str(l).lower() for l in langs}
        if langs_lc and "en" not in langs_lc:
            return None

        # 2) Text presence / normalize / length
        raw = post.get("text")
        if not isinstance(raw, str):
            return None
        text = self._collapse_ws(raw)
        if len(text) < self.min_len:
            return None
        text = text[: self.max_len]

        # 3) Noise-only drop: no alphanumeric tokens after scrubbing
        if self.drop_noise_only and self._noise_only(text):
            return None

        # 4) English-only charset (ASCII + allowed extras)
        if self.enforce_english_charset and not self._english_charset_ok(text, self.allowed_extras):
            return None

        # 5) Write back normalized/truncated text
        post["text"] = text
        return post

    # Optional sugar: allow instance to be called like a function
    __call__ = run

    # ---- helpers ----
    @staticmethod
    def _collapse_ws(s: str) -> str:
        return re.sub(r"\s+", " ", s).strip()

    @classmethod
    def _noise_only(cls, s: str) -> bool:
        cleaned = cls.URL_RE.sub(" ", s)
        cleaned = cls.MENTION_RE.sub(" ", cleaned)
        cleaned = cls.HASHTAG_RE.sub(" ", cleaned)
        cleaned = cls.EMOJI_RE.sub(" ", cleaned)
        tokens = re.findall(r"[A-Za-z0-9]+", cleaned)
        return len(tokens) == 0

    @staticmethod
    def _english_charset_ok(s: str, allowed_extras: str) -> bool:
        for ch in s:
            if ch.isascii():
                o = ord(ch)
                if ch.isspace() or 32 <= o <= 126:
                    continue
                return False
            if ch in allowed_extras:
                continue
            return False
        return True
