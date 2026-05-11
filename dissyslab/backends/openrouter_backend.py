# dissyslab/backends/openrouter_backend.py

"""
OpenRouter backend — a single gateway to many open-source SLMs.

OpenRouter (https://openrouter.ai) is a hosted API that proxies to
dozens of models — Qwen, Llama, Mistral, DeepSeek, plus the closed
ones — behind a single OpenAI-compatible endpoint. We use it as the
*experimental* backend for the SLM-viability work described in
``dev/PLAN_free_ai_for_pat.md``: it lets us iterate cheaply on
prompts and compare models without each one needing its own SDK.

In production, Pat runs Ollama locally with the same model. Same
prompts, same model name, different inference path.

Configuration
=============

Two environment variables:

* ``OPENROUTER_API_KEY`` — required. Get one at openrouter.ai/keys.
  Charged against OpenRouter credits unless BYOK is configured for
  the upstream provider.
* ``OPENROUTER_MODEL`` — optional. Default model identifier. Format
  matches OpenRouter's catalogue, e.g. ``"qwen/qwen-2.5-7b-instruct"``,
  ``"meta-llama/llama-3.1-8b-instruct"``, ``"anthropic/claude-sonnet-4"``.
  When unset, falls back to ``DEFAULT_MODEL`` below.

Per-call ``model`` kwarg overrides the env var.

Example
=======

::

    export OPENROUTER_API_KEY=sk-or-v1-...
    export OPENROUTER_MODEL=qwen/qwen-2.5-7b-instruct
    export DSL_BACKEND=openrouter

then any office or eval harness will route through Qwen via
OpenRouter.

Design notes
============

- Uses ``requests`` synchronously. No streaming. The role/agent
  abstraction calls one prompt at a time; complications like
  streaming live above this layer.
- The client is constructed lazily on first ``complete`` call,
  matching ``AnthropicBackend``.
- Adds OpenRouter's recommended ``HTTP-Referer`` and ``X-Title``
  headers so usage shows up under a recognisable label in the
  OpenRouter dashboard.
- On HTTP errors the response body is included in the raised
  exception — OpenRouter's error JSON usually contains the actual
  diagnostic, which would otherwise be hidden behind a bare
  ``HTTPError``.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional

import requests


DEFAULT_MODEL = "qwen/qwen3.5-35b-a3b"
"""Default model when neither ``OPENROUTER_MODEL`` nor the per-call
``model=`` kwarg is set.

Why this one (as of 2026-05): Qwen3.5-35B-A3B is the Qwen team's
current open-weight MoE — 35B total parameters, 3B active per token
via routing, native vision-language hybrid with linear attention.
Quality is comparable to the dense Qwen3.5-27B; inference cost per
call is the much cheaper 3B-active path. Weights are openly
published on HuggingFace, so Pat can run the same model locally
once Ollama adds it (until then she runs the architecturally
similar Qwen3-30B-A3B, available today as ``qwen3:30b`` on Ollama).

Pricing on OpenRouter: $0.25 / M input tokens, $2 / M output
tokens. Phase 1 experiments cost well under $5 total.

Override per-experiment with ``OPENROUTER_MODEL`` env var or the
``model=`` kwarg to ``complete()``."""


_ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"


class OpenRouterBackend:
    """Concrete Backend backed by OpenRouter's chat-completions API."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        timeout: float = 60.0,
    ) -> None:
        """
        Args:
            api_key: OpenRouter API key. If None, read from
                     ``OPENROUTER_API_KEY`` at first ``complete`` call.
            model:   Default model. If None, read from
                     ``OPENROUTER_MODEL`` env var; otherwise
                     ``DEFAULT_MODEL``.
            timeout: HTTP request timeout in seconds. Default 60s
                     covers slow SLMs without hanging indefinitely.
        """
        self._api_key = api_key
        self._default_model = model
        self._timeout = timeout

    def _resolve_api_key(self) -> str:
        api_key = self._api_key or os.environ.get("OPENROUTER_API_KEY")
        if not api_key:
            raise ValueError(
                "OPENROUTER_API_KEY not set in environment.\n\n"
                "To fix this:\n"
                "1. Get an API key from: https://openrouter.ai/keys\n"
                "2. Set environment variable: "
                "export OPENROUTER_API_KEY='your-key-here'\n"
                "3. Add credits at https://openrouter.ai/credits "
                "(a few dollars covers Phase 1 experiments)."
            )
        return api_key

    def _resolve_model(self, override: Optional[str]) -> str:
        if override:
            return override
        if self._default_model:
            return self._default_model
        env_model = os.environ.get("OPENROUTER_MODEL")
        if env_model:
            return env_model
        return DEFAULT_MODEL

    def complete(
        self,
        *,
        system: str,
        user: str,
        max_tokens: int = 8192,
        temperature: float = 1.0,
        model: Optional[str] = None,
    ) -> str:
        # NOTE: max_tokens default is 8192, not 1024 like the
        # AnthropicBackend. Many open-weight models on OpenRouter
        # (Qwen3.5-A3B, DeepSeek-V3, etc.) are reasoning-enabled by
        # default and use a substantial fraction of max_tokens for
        # internal chain-of-thought before producing the final
        # completion.
        #
        # Empirical calibration on Qwen3.5-35B-A3B over the
        # situation_room corpus:
        #   max_tokens=1024 → many calls return ``content=None``
        #                     (reasoning ate the budget).
        #   max_tokens=4096 → ~50% empty rate on complex roles
        #                     (entity_extractor was 100% empty).
        #   max_tokens=8192 → 25/25 returned valid JSON. The right
        #                     default for current reasoning-heavy SLMs.
        """
        Send a single system + user prompt to OpenRouter and return
        the raw text of the assistant reply.

        See ``dissyslab.backends.base.Backend.complete`` for the full
        contract.
        """
        api_key = self._resolve_api_key()
        model_id = self._resolve_model(model)

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            # OpenRouter's recommended discoverability headers — show
            # up in the dashboard so we can attribute spend.
            "HTTP-Referer": "https://github.com/kmchandy/DisSysLab",
            "X-Title": "DisSysLab",
        }
        payload: Dict[str, Any] = {
            "model": model_id,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        try:
            response = requests.post(
                _ENDPOINT,
                headers=headers,
                data=json.dumps(payload),
                timeout=self._timeout,
            )
        except requests.RequestException as exc:
            raise RuntimeError(
                f"OpenRouter request failed: {exc}"
            ) from exc

        if response.status_code != 200:
            # Surface the body — OpenRouter's error JSON usually
            # contains the actual diagnostic.
            raise RuntimeError(
                f"OpenRouter HTTP {response.status_code}: "
                f"{response.text}"
            )

        try:
            body = response.json()
        except ValueError as exc:
            raise RuntimeError(
                f"OpenRouter returned non-JSON response: "
                f"{response.text[:500]}"
            ) from exc

        # OpenAI-compatible shape: choices[0].message.content
        try:
            return body["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError(
                f"OpenRouter response missing expected fields: "
                f"{body}"
            ) from exc
