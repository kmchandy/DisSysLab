# llm_enricher.py
from __future__ import annotations
from typing import Any, Callable, Dict, Optional, Sequence, Union

TextGetter = Union[str, Sequence[str], Callable[[Dict[str, Any]], str]]
LLMFn = Callable[[str], Dict[str, Any]]                # text -> dict
# system_prompt -> (text -> dict)
LLMBuilder = Callable[[str], LLMFn]
KeepWhen = Callable[[Dict[str, Any], Dict[str, Any]], bool]


class LLMEnricher:
    """
    Generic LLM node: extract text, (optionally) filter by language/length,
    call an LLM that was constructed ONCE with a system prompt, then enrich msg.

    Construction
    ------------
    Provide either:
      • llm_fn: a ready-to-use callable text -> dict, OR
      • llm_builder + system_prompt: we'll build llm_fn once in __init__.

    Key params
    ----------
    system_prompt : str | None
        System prompt to initialize the LLM agent. Required if llm_builder is used.
    llm_builder : Callable[[str], Callable[[str], dict]] | None
        Factory that takes system_prompt and returns a text->dict function.
    llm_fn : Callable[[str], dict] | None
        Already-built LLM callable. If given, system_prompt/llm_builder are ignored.

    text_getter : str | Sequence[str] | Callable[[dict], str]
        Where to pull the text from (e.g., "page_text", ("page_text","text")).
    out_ns, field_mapping, keep_when, pass_context, max_text_len
        Same as before (pass_context is kept for API parity but unused when llm_fn(text) only).

    Filters
    -------
    min_len : int (default 0)              # do not call LLM if len(text) < min_len
    require_langs : Sequence[str] | None   # enforce if msg["lang"] exists; default ("en",)
    drop_on_filter : bool (default True)   # drop when filtered; else pass through unchanged
    """

    def __init__(
        self,
        *,
        # LLM creation
        system_prompt: Optional[str] = None,
        llm_builder: Optional[LLMBuilder] = None,
        llm_fn: Optional[LLMFn] = None,
        # Merge behavior
        text_getter: TextGetter = ("page_text", "text"),
        out_ns: Optional[str] = "llm",
        field_mapping: Optional[Dict[str, str]] = None,
        keep_when: Optional[KeepWhen] = None,
        max_text_len: Optional[int] = None,
        # Filters
        min_len: int = 0,
        require_langs: Optional[Sequence[str]] = ("en",),
        drop_on_filter: bool = True,
        # Misc
        name: Optional[str] = None,
    ) -> None:
        # Build or accept the LLM callable (created ONCE)
        if llm_fn is not None:
            self.llm_fn = llm_fn
        else:
            if llm_builder is None or not system_prompt:
                raise ValueError(
                    "Provide llm_fn OR (llm_builder AND system_prompt).")
            self.llm_fn = llm_builder(system_prompt)

        self.text_getter = text_getter
        self.out_ns = out_ns
        self.field_mapping = dict(field_mapping or {})
        self.keep_when = keep_when
        self.max_text_len = max_text_len if (
            max_text_len and max_text_len > 0) else None

        self.min_len = int(min_len)
        self.require_langs = tuple(
            require_langs) if require_langs is not None else None
        self.drop_on_filter = bool(drop_on_filter)

        self._name = name or self.__class__.__name__

    @property
    def __name__(self) -> str:
        return self._name

    def __call__(self, msg: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        text = self._get_text(msg)
        if not text:
            return None if self.drop_on_filter else msg

        # Language gate (only if lang hints exist)
        if self.require_langs is not None:
            langs = msg.get("lang") or []
            if langs and not any(l in self.require_langs for l in langs):
                return None if self.drop_on_filter else msg

        # Length gate
        if self.min_len and len(text) < self.min_len:
            return None if self.drop_on_filter else msg

        if self.max_text_len:
            text = text[: self.max_text_len]

        # Call the prebuilt LLM (text only)
        out = self.llm_fn(text)
        if not isinstance(out, dict):
            return None if self.drop_on_filter else msg

        # Optional keep predicate
        if self.keep_when is not None and not self.keep_when(msg, out):
            return None if self.drop_on_filter else msg

        # Merge
        enriched = dict(msg)
        if self.out_ns is not None:
            enriched[self.out_ns] = out
        if self.field_mapping:
            for ok, mk in self.field_mapping.items():
                if ok in out:
                    enriched[mk] = out[ok]
        if self.out_ns is None and not self.field_mapping:
            enriched.update(out)  # shallow merge
        return enriched

    # helpers
    def _get_text(self, msg: Dict[str, Any]) -> str:
        g = self.text_getter
        if callable(g):
            v = g(msg)
            return v.strip() if isinstance(v, str) else ""
        if isinstance(g, str):
            v = msg.get(g)
            return v.strip() if isinstance(v, str) else ""
        for key in g:  # sequence
            v = msg.get(key)
            if isinstance(v, str) and v.strip():
                return v.strip()
        return ""
