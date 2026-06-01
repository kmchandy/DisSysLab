# dissyslab/backends/gemini_backend.py

"""
Google AI Studio backend — serves both Gemini and Gemma model families.

Google's free-tier AI Studio API (https://aistudio.google.com) exposes
two related model families through a single endpoint:

* **Gemini** — proprietary frontier models (gemini-2.5-flash,
  gemini-2.5-pro, etc.). Free tier with generous rate limits.
* **Gemma** — open-weight models (gemma-3-27b-it, gemma-3-12b-it,
  etc.). Also free, served through the same API path.

One backend class handles both. The model name selects which family
you get; the request shape and authentication are identical.

Configuration
=============

One environment variable:

* ``GEMINI_API_KEY`` — required. Get one at
  https://aistudio.google.com/apikey (free, no credit card; just a
  Google account). The class also accepts ``GOOGLE_API_KEY`` as a
  fallback so users who set the more generic name still work.

* ``GEMINI_MODEL`` — optional. Default model identifier. Examples:
  ``"gemini-2.5-flash"`` (Gemini), ``"gemma-3-27b-it"`` (Gemma).
  When unset, falls back to ``DEFAULT_MODEL`` below.

Per-call ``model`` kwarg overrides the env var.

Example
=======

::

    export GEMINI_API_KEY=AIzaSy...
    export DSL_BACKEND=gemma            # picks the Gemma default model
    dsl run dissyslab/gallery/apps/debate/

Or per-agent in office.md::

    Gemma is a gemma.
    Gemma's AI is gemma.                # uses the gemma registry variant
    Claude is a claude.
    Claude's AI is anthropic.

Design notes
============

- Uses ``requests`` synchronously. No streaming. Mirrors
  ``OpenRouterBackend`` and ``OllamaBackend`` so the dependency
  surface stays tiny.
- The API key is read lazily on first ``complete`` call. Construction
  does not hit the network.
- System instructions go in the API's dedicated
  ``systemInstruction`` field (supported on Gemini 1.5+ and all
  Gemma 2/3 instruct models). If you point this backend at an older
  model that doesn't support it, the API returns a 400 — switch to
  a current model.
- Gemma models on this API are the official Google-hosted variants,
  not community quantizations. Quality is closer to what the model
  card describes.
- Errors include the response body so Google's diagnostic JSON
  (often quite informative) is visible.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional

import requests


DEFAULT_MODEL = "gemma-4-31b-it"
"""Default model when neither ``GEMINI_MODEL`` nor the per-call
``model=`` kwarg is set.

Why this one (as of 2026-05): ``gemma-4-31b-it`` is the dense
31B-parameter Gemma 4 instruction-tuned model. It's the largest
non-MoE Gemma currently served on the free tier of Google AI Studio.

For higher throughput at the cost of some quality, the MoE variant
``gemma-4-26b-a4b-it`` (4B active params) is also available.

For Gemini instead of Gemma, override per-call with
``model="gemini-2.5-flash"`` or globally with
``export GEMINI_MODEL=gemini-2.5-flash``. Both Gemini Flash and
Gemma 4 models share Google AI Studio's generous free tier."""

DEFAULT_TEMPERATURE = 1.0
DEFAULT_MAX_TOKENS = 2048


_ENDPOINT_TEMPLATE = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "{model}:generateContent"
)


class GeminiBackend:
    """Concrete Backend backed by Google AI Studio's REST API.

    Serves both Gemini and Gemma model families — pick by model name.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        timeout: float = 60.0,
    ) -> None:
        """
        Args:
            api_key: Google AI Studio key. If None, read from
                     ``GEMINI_API_KEY`` (or fallback ``GOOGLE_API_KEY``)
                     at first ``complete`` call.
            model:   Default model identifier. If None, read from
                     ``GEMINI_MODEL`` env var; otherwise
                     ``DEFAULT_MODEL``.
            temperature: Default sampling temperature. If None, uses
                     DEFAULT_TEMPERATURE. Named backend variants
                     (gemma_creative, gemini_precise, etc.) bake a
                     specific value in here.
            max_tokens: Default max-tokens cap. If None, uses
                     DEFAULT_MAX_TOKENS.
            timeout: HTTP request timeout in seconds.
        """
        self._api_key = api_key
        self._default_model = model
        self._default_temperature = (
            temperature if temperature is not None else DEFAULT_TEMPERATURE
        )
        self._default_max_tokens = (
            max_tokens if max_tokens is not None else DEFAULT_MAX_TOKENS
        )
        self._timeout = timeout

    def _resolve_api_key(self) -> str:
        # Accept either name — Google's official docs use both
        # interchangeably and users may have either in their shell rc.
        api_key = (
            self._api_key
            or os.environ.get("GEMINI_API_KEY")
            or os.environ.get("GOOGLE_API_KEY")
        )
        if not api_key:
            raise ValueError(
                "GEMINI_API_KEY not set in environment.\n\n"
                "To fix this:\n"
                "1. Get a free API key from: "
                "https://aistudio.google.com/apikey\n"
                "2. Set environment variable: "
                "export GEMINI_API_KEY='your-key-here'\n"
                "3. Add to ~/.zshrc or ~/.bashrc so it persists "
                "across terminals.\n\n"
                "Google AI Studio's free tier is generous (tens of "
                "thousands of requests per day for Gemma and Gemini "
                "Flash models). No credit card required."
            )
        return api_key

    def _resolve_model(self, override: Optional[str]) -> str:
        if override:
            return override
        if self._default_model:
            return self._default_model
        env_model = os.environ.get("GEMINI_MODEL")
        if env_model:
            return env_model
        return DEFAULT_MODEL

    def complete(
        self,
        *,
        system: str,
        user: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        model: Optional[str] = None,
    ) -> str:
        """
        Send a single system + user prompt to Google AI Studio and
        return the raw text of the assistant reply.

        See ``dissyslab.backends.base.Backend.complete`` for the full
        contract. ``max_tokens``, ``temperature`` and ``model`` fall
        back to the instance defaults set in ``__init__`` when the
        caller passes ``None``.
        """
        api_key = self._resolve_api_key()
        model_id = self._resolve_model(model)

        effective_temperature = (
            temperature if temperature is not None
            else self._default_temperature
        )
        effective_max_tokens = (
            max_tokens if max_tokens is not None
            else self._default_max_tokens
        )

        url = _ENDPOINT_TEMPLATE.format(model=model_id)
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": api_key,
        }
        payload: Dict[str, Any] = {
            "contents": [
                {"role": "user", "parts": [{"text": user}]},
            ],
            "systemInstruction": {
                "parts": [{"text": system}],
            },
            "generationConfig": {
                "temperature": effective_temperature,
                "maxOutputTokens": effective_max_tokens,
            },
        }

        try:
            response = requests.post(
                url,
                headers=headers,
                data=json.dumps(payload),
                timeout=self._timeout,
            )
        except requests.RequestException as exc:
            raise RuntimeError(
                f"Google AI Studio request failed: {exc}"
            ) from exc

        if response.status_code != 200:
            raise RuntimeError(
                f"Google AI Studio HTTP {response.status_code}: "
                f"{response.text}"
            )

        try:
            body = response.json()
        except ValueError as exc:
            raise RuntimeError(
                f"Google AI Studio returned non-JSON response: "
                f"{response.text[:500]}"
            ) from exc

        # Gemini/Gemma response shape:
        #   {"candidates": [{"content": {"parts": [{"text": "..."}]}}], ...}
        # When the model returns nothing (e.g. safety filter triggered),
        # candidates may exist without a "parts" field. Surface that as
        # an explicit RuntimeError rather than a KeyError.
        try:
            candidate = body["candidates"][0]
            parts = candidate["content"]["parts"]
            return parts[0]["text"]
        except (KeyError, IndexError, TypeError) as exc:
            # Common case: safety filter or empty response.
            finish_reason = (
                body.get("candidates", [{}])[0].get("finishReason")
                if body.get("candidates")
                else None
            )
            raise RuntimeError(
                f"Google AI Studio response missing expected fields "
                f"(finishReason={finish_reason!r}): {body}"
            ) from exc
