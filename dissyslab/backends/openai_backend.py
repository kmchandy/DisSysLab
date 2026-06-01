# dissyslab/backends/openai_backend.py

"""
OpenAI backend — direct access to OpenAI's chat-completions API.

OpenAI's hosted models (GPT-4o, GPT-5, o-series reasoning models)
are accessed through ``api.openai.com``. The REST shape is identical
to OpenRouter's because OpenRouter was built to be OpenAI-compatible
— in fact this backend is essentially OpenRouter's twin with a
different endpoint URL, no proxy-attribution headers, and a
different API key env var.

Configuration
=============

Two environment variables:

* ``OPENAI_API_KEY`` — required. Get one at platform.openai.com.
  Charged against your OpenAI billing account.
* ``OPENAI_MODEL`` — optional. Default model identifier. Examples:
  ``"gpt-4o-mini"``, ``"gpt-4o"``, ``"gpt-5"``, ``"gpt-5-mini"``,
  ``"o3-mini"``. When unset, falls back to ``DEFAULT_MODEL`` below.

Per-call ``model`` kwarg overrides the env var.

Example
=======

::

    export OPENAI_API_KEY=sk-proj-...
    export DSL_BACKEND=openai
    dsl run dissyslab/gallery/apps/debate/

Or per-agent in office.md::

    GPT is a gpt.
    GPT's AI is openai.

Design notes
============

- Uses ``requests`` synchronously. No streaming. Same dependency
  surface as the OpenRouter and Ollama backends — no separate
  ``openai`` Python SDK needed.
- The API key is read lazily on first ``complete`` call.
- On HTTP errors the response body is included in the raised
  exception so OpenAI's diagnostic JSON (usually informative) is
  visible.
- Reasoning models (``o1``, ``o3``, ``o3-mini``, ...) use a slightly
  different parameter scheme — they don't accept ``temperature``
  and use ``max_completion_tokens`` instead of ``max_tokens``. The
  current backend always passes the older field names, which works
  for GPT-4o / GPT-5 family; if you point this backend at an o-series
  reasoning model, OpenAI returns HTTP 400 and the diagnostic JSON
  will say which field to drop. Reasoning models can be supported
  cleanly later by registering a separate ``openai_reasoning``
  variant with adjusted call shape — out of scope for the current
  debate office.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional

import requests


DEFAULT_MODEL = "gpt-4o-mini"
"""Default model when neither ``OPENAI_MODEL`` nor the per-call
``model=`` kwarg is set.

Why this one: ``gpt-4o-mini`` is OpenAI's cheap, fast workhorse —
roughly $0.15 / M input tokens, $0.60 / M output tokens at time of
writing. Quality is more than enough for the s-t-r role workloads
in this framework. For Pat's debate office that fires one OpenAI
call per round, total cost per debate is essentially zero.

Pick a different default by setting ``OPENAI_MODEL`` in your shell
or passing ``model=`` per-call. ``gpt-5-mini`` or ``gpt-5`` are
reasonable upgrades when quality matters more than cost."""

DEFAULT_TEMPERATURE = 1.0
DEFAULT_MAX_TOKENS = 2048


_ENDPOINT = "https://api.openai.com/v1/chat/completions"


class OpenAIBackend:
    """Concrete Backend backed by OpenAI's chat-completions API."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        timeout: float = 60.0,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> None:
        """
        Args:
            api_key: OpenAI API key. If None, read from
                     ``OPENAI_API_KEY`` at first ``complete`` call.
            model:   Default model. If None, read from
                     ``OPENAI_MODEL`` env var; otherwise
                     ``DEFAULT_MODEL``.
            timeout: HTTP request timeout in seconds. Default 60s.
            temperature: Default sampling temperature when
                     ``complete(temperature=None)``. If None, uses
                     DEFAULT_TEMPERATURE. Named variants
                     (openai_creative, openai_precise) bake a
                     specific value in here.
            max_tokens: Default max-tokens cap when
                     ``complete(max_tokens=None)``. If None, uses
                     DEFAULT_MAX_TOKENS.
        """
        self._api_key = api_key
        self._default_model = model
        self._timeout = timeout
        self._default_temperature = (
            temperature if temperature is not None else DEFAULT_TEMPERATURE
        )
        self._default_max_tokens = (
            max_tokens if max_tokens is not None else DEFAULT_MAX_TOKENS
        )

    def _resolve_api_key(self) -> str:
        api_key = self._api_key or os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY not set in environment.\n\n"
                "To fix this:\n"
                "1. Get an API key from: https://platform.openai.com/api-keys\n"
                "2. Set environment variable: "
                "export OPENAI_API_KEY='your-key-here'\n"
                "3. Add to ~/.zshrc or ~/.bashrc so it persists "
                "across terminals.\n\n"
                "Note: OpenAI charges per call (typically <$0.01 "
                "per role invocation on gpt-4o-mini)."
            )
        return api_key

    def _resolve_model(self, override: Optional[str]) -> str:
        if override:
            return override
        if self._default_model:
            return self._default_model
        env_model = os.environ.get("OPENAI_MODEL")
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
        Send a single system + user prompt to OpenAI and return the
        raw text of the assistant reply.

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

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload: Dict[str, Any] = {
            "model": model_id,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "max_tokens": effective_max_tokens,
            "temperature": effective_temperature,
        }

        try:
            response = requests.post(
                _ENDPOINT,
                headers=headers,
                data=json.dumps(payload),
                timeout=self._timeout,
            )
        except requests.RequestException as exc:
            raise RuntimeError(f"OpenAI request failed: {exc}") from exc

        if response.status_code != 200:
            # Surface the body — OpenAI's error JSON typically names
            # the exact field at fault (e.g. unsupported parameter
            # for o-series reasoning models).
            raise RuntimeError(
                f"OpenAI HTTP {response.status_code}: {response.text}"
            )

        try:
            body = response.json()
        except ValueError as exc:
            raise RuntimeError(
                f"OpenAI returned non-JSON response: "
                f"{response.text[:500]}"
            ) from exc

        # OpenAI shape: choices[0].message.content
        try:
            return body["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError(
                f"OpenAI response missing expected fields: {body}"
            ) from exc
