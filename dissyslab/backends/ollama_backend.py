# dissyslab/backends/ollama_backend.py

"""
Ollama backend — local AI inference, free, no API key.

[Ollama](https://ollama.com) runs open-weight language models on
your laptop. DisSysLab's free-AI-for-Pat positioning depends on
this being a viable production backend, not just a hobby setup.

This backend uses Ollama's OpenAI-compatible chat endpoint, so the
request shape is the same as OpenRouter's; only the URL differs
and no auth header is needed.

Configuration
=============

One environment variable, with a sensible default:

* ``OLLAMA_MODEL`` — optional. Default model identifier. Format
  matches Ollama's local catalogue:
  ``"qwen3:30b"``, ``"qwen3:8b"``, ``"llama3.1:8b"``, etc.
  Defaults to ``"qwen3:30b"`` (the recommended Pat-facing model).

* ``OLLAMA_HOST`` — optional. Defaults to
  ``"http://127.0.0.1:11434"`` (Ollama's local default).
  Override if you're running Ollama remotely or on a non-default
  port.

Per-call ``model`` kwarg overrides the env var.

Example
=======

::

    # 1. Install and start Ollama (see https://ollama.com)
    # 2. Pull the model
    ollama pull qwen3:30b

    # 3. Use it
    export DSL_BACKEND=ollama
    dsl run dissyslab/gallery/apps/situation_room/

Notes
=====

- Ollama uses no API key; the absence of one is the point. We do
  not raise on missing credentials.
- Cold-start time can be long (model load into VRAM/RAM the first
  time). Subsequent calls are faster.
- This backend assumes Ollama is reachable on ``OLLAMA_HOST``. If
  the service isn't running, calls fail with a connection-refused
  error.
- ``max_tokens`` default is 8192 — same as OpenRouter, calibrated
  for reasoning-enabled SLMs that spend a substantial fraction of
  their budget on internal chain-of-thought.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional

import requests


DEFAULT_MODEL = "qwen3:30b"
"""Default Ollama model when neither ``OLLAMA_MODEL`` nor the
per-call ``model=`` kwarg is set.

Why this one: ``qwen3:30b`` (Qwen3-30B-A3B) is the Qwen team's
current open-weight MoE in the size class that fits a 32 GB Mac
with margin. It's architecturally similar to the
Qwen3.5-35B-A3B used in our OpenRouter validation runs, with
acceptable-to-better quality for Pat-B's situation-room office."""

DEFAULT_TEMPERATURE = 1.0
DEFAULT_MAX_TOKENS = 8192


def _default_host() -> str:
    return os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")


class OllamaBackend:
    """Concrete Backend backed by a local Ollama server."""

    def __init__(
        self,
        host: Optional[str] = None,
        model: Optional[str] = None,
        timeout: float = 600.0,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> None:
        """
        Args:
            host: Base URL for Ollama, e.g. ``"http://127.0.0.1:11434"``.
                  If None, read from ``OLLAMA_HOST`` env var; otherwise
                  use Ollama's local default.
            model: Default model identifier (e.g. ``"qwen3:30b"``).
                   If None, read from ``OLLAMA_MODEL``; otherwise
                   use ``DEFAULT_MODEL``.
            timeout: HTTP request timeout in seconds. Default 600s
                     (10 minutes) — local SLM inference on a typical
                     Mac can take ~30 seconds per call, and slow
                     hardware on a cold start can be much slower.
            temperature: Default sampling temperature when
                     ``complete(temperature=None)``. If None, uses
                     DEFAULT_TEMPERATURE. Named backend variants
                     (ollama_creative, ollama_precise) bake a specific
                     value in here.
            max_tokens: Default max-tokens cap when
                     ``complete(max_tokens=None)``. If None, uses
                     DEFAULT_MAX_TOKENS.
        """
        self._host = host
        self._default_model = model
        self._timeout = timeout
        self._default_temperature = (
            temperature if temperature is not None else DEFAULT_TEMPERATURE
        )
        self._default_max_tokens = (
            max_tokens if max_tokens is not None else DEFAULT_MAX_TOKENS
        )

    def _resolve_host(self) -> str:
        return self._host or _default_host()

    def _resolve_model(self, override: Optional[str]) -> str:
        if override:
            return override
        if self._default_model:
            return self._default_model
        env_model = os.environ.get("OLLAMA_MODEL")
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
        Send a single system + user prompt to Ollama and return the
        raw text of the assistant reply.

        See ``dissyslab.backends.base.Backend.complete`` for the full
        contract. ``max_tokens``, ``temperature`` and ``model`` fall
        back to the instance defaults set in ``__init__`` when the
        caller passes ``None``.
        """
        host = self._resolve_host().rstrip("/")
        model_id = self._resolve_model(model)
        url = f"{host}/v1/chat/completions"

        effective_temperature = (
            temperature if temperature is not None
            else self._default_temperature
        )
        effective_max_tokens = (
            max_tokens if max_tokens is not None
            else self._default_max_tokens
        )

        headers = {"Content-Type": "application/json"}
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
                url,
                headers=headers,
                data=json.dumps(payload),
                timeout=self._timeout,
            )
        except requests.ConnectionError as exc:
            raise RuntimeError(
                f"Ollama not reachable at {host}. Is the service "
                f"running? Try: ollama serve\n  (underlying: {exc})"
            ) from exc
        except requests.RequestException as exc:
            raise RuntimeError(f"Ollama request failed: {exc}") from exc

        if response.status_code != 200:
            raise RuntimeError(
                f"Ollama HTTP {response.status_code}: {response.text}"
            )

        try:
            body = response.json()
        except ValueError as exc:
            raise RuntimeError(
                f"Ollama returned non-JSON response: {response.text[:500]}"
            ) from exc

        try:
            return body["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError(
                f"Ollama response missing expected fields: {body}"
            ) from exc
