# llm_topic_filter.py
from __future__ import annotations
import json
from typing import Any, Callable, Dict, List, Optional, Sequence


class LLMTopicFilter:
    """
    LLM-based topic relevance filter for short posts.

    Parameters
    ----------
    topics : Sequence[str]
        Topic names to filter (e.g., ["AI","jobs","space"]).
    llm_fn : Callable[[str], Dict[str, Any]]
        Function that takes a prompt string and returns a dict with keys:
          - "labels": list[str]
          - "scores": dict[str, float]
          - "primary": str | None
        (You provide this; see stub below.)
    name : str | None, default None
        Optional display name for DSLs that read `fn.__name__`.

    Returns
    -------
    Optional[Dict[str, Any]]
        - dict: original message plus annotations (if attach_scores=True), when relevant
        - None: when no topic crosses the threshold
    """

    def __init__(
        self,
        *,
        topics: Sequence[str],
        llm_fn: Callable[[str], Dict[str, Any]],
        name: Optional[str] = None,
    ) -> None:
        self.topics = list(topics)
        self.llm_fn = llm_fn
        self._name = name or self.__class__.__name__

    @property
    def __name__(self) -> str:
        return self._name

    def _build_prompt(self, text: str) -> str:
        topics_json = json.dumps(self.topics, ensure_ascii=False)
        synonyms_json = json.dumps(self.synonyms, ensure_ascii=False)
        # System+user fused in one string (adjust if your client separates roles)
        return (
            "You are a topic tagger. Given a short social-media post, score its relevance to the provided topics.\n\n"
            "Rules:\n"
            "- Return ONLY a single JSON object with keys exactly:\n"
            '  "labels" (array of topic strings),\n'
            '  "scores" (object: topic → number 0..1),\n'
            '  "primary" (string or null).\n'
            "- Do not include explanations, markdown, or extra fields.\n"
            "- A topic is relevant if the main idea clearly concerns it, including close synonyms.\n"
            "- Ignore sarcasm markers and hashtags that do not change the core meaning.\n\n"
            "Scoring guidance:\n"
            "- 1.0 = clearly about this topic; 0.7 = mostly about it; 0.4 = tangential; 0.0 = unrelated.\n\n"
            f"Topics:\n{topics_json}\n\n"
            f"Synonym hints (non-exhaustive):\n{synonyms_json}\n\n"
            f"Text:\n{text}"
        )

    def __call__(self, msg: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        text = (msg.get("page_text") or msg.get("text") or "").strip()
        if not text:
            return None

        prompt = self._build_prompt(text)
        # must return a dict with labels/scores/primary
        out = self.llm_fn(prompt)

        # Validate shape defensively
        labels = list(out.get("labels") or [])
        scores: Dict[str, float] = dict(out.get("scores") or {})
        primary = out.get("primary")

        # Normalize: ensure topics subset + scores for all topics (0.0 default)
        labels = [t for t in labels if t in self.topics]
        scores = {t: float(scores.get(t, 0.0)) for t in self.topics}

        # Optionally keep only top-k labels for annotation
        if self.top_k:
            top = sorted(self.topics, key=lambda t: scores[t], reverse=True)[
                : self.top_k]
            labels = [t for t in labels if t in top]

        # Relevance decision
        keep = any(s >= self.threshold for s in scores.values())
        if not keep:
            return None

        if self.attach_scores:
            out_msg = dict(msg)
            out_msg["topic_labels"] = labels
            out_msg["topic_scores"] = scores
            out_msg["primary_topic"] = primary if (isinstance(
                primary, str) and primary in self.topics) else None
            return out_msg
        return msg
