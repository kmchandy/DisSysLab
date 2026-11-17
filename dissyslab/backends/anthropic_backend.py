# dissyslab/backends/anthropic_backend.py

"""
Anthropic (Claude) backend — the default and currently only backend.

Wraps `anthropic.Anthropic().messages.create(...)` behind the Backend
Protocol. All existing DisSysLab call paths (student-runtime
`ai_agent`, the build-time compiler in `office/utils.py` and
`office/make_network.py`) route through this class.

Design notes:

- The client is constructed lazily on first `complete` call, not at
  import time. This lets tests and alternative backends swap the
  implementation via `DSL_BACKEND` without a stray `Anthropic()`
  call escaping.
- The missing-key `ValueError` text below is intentionally identical
  in shape to the text that used to live in `ai_agent.py`, so the
  CLI triage in `cli.py` still recognizes it and prints the Path-A
  `.env` fix hint instead of a raw traceback.
- `complete` returns `message.content[0].text` *without* `.strip()`.
  Strip-and-parse is the caller's job (matches the previous
  behavior in `ai_agent.py`, where stripping happens after receiving
  the text).
"""

from __future__ import annotations

import os
from typing import Any, Optional

from anthropic import Anthropic


DEFAULT_MODEL = "claude-haiku-5-5"
"""The model when neither ``ANTHROPIC_MODEL`` nor ``model=`` says otherwise.

Haiku 5.5 (November 2026): the cheapest current Claude model, about
$0.10 / M input and $0.50 / M output tokens for prompts under 100K, some
25 times cheaper than the previous default, ``claude-sonnet-4-5``. A
course office's replies are short JSON objects, and with a reply schema
(``complete(schema=...)``) their shape is enforced by the API, so the
cheapest model is enough. Set ``ANTHROPIC_MODEL`` to use another."""
DEFAULT_TEMPERATURE = 1.0
DEFAULT_MAX_TOKENS = 1024


class AnthropicBackend:
    """Concrete Backend backed by the Anthropic Claude API."""

    #: ``complete(schema=...)`` is honoured: the API constrains the reply
    #: to the JSON schema (structured outputs, ``output_config.format``).
    supports_schema = True

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> None:
        """
        Args:
            api_key: Anthropic API key. If None, read from
                     ANTHROPIC_API_KEY at first `complete` call.
            model:   Default model to use when `complete(model=None)`.
                     If None, uses ANTHROPIC_MODEL if set, else
                     DEFAULT_MODEL.
            temperature: Default sampling temperature when
                     ``complete(temperature=None)``. If None, uses
                     DEFAULT_TEMPERATURE. Named backend variants
                     (anthropic_creative, anthropic_precise) bake a
                     specific value in here so the office writer
                     does not have to think about temperature
                     numbers — they pick a persona instead.
            max_tokens: Default max-tokens cap when
                     ``complete(max_tokens=None)``. If None, uses
                     DEFAULT_MAX_TOKENS.
        """
        self._api_key = api_key
        self._default_model = model or os.environ.get("ANTHROPIC_MODEL") or DEFAULT_MODEL
        self._default_temperature = (
            temperature if temperature is not None else DEFAULT_TEMPERATURE
        )
        self._default_max_tokens = (
            max_tokens if max_tokens is not None else DEFAULT_MAX_TOKENS
        )
        self._client: Optional[Anthropic] = None

    def _get_client(self) -> Anthropic:
        """Lazy-construct the Anthropic client. Raises if no key."""
        if self._client is not None:
            return self._client

        api_key = self._api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            # NOTE: this text is matched by cli.py triage on the
            # substring "anthropic_api_key" + "not set". Do not
            # rewrite without also updating cli.py.
            raise ValueError(
                "ANTHROPIC_API_KEY not set in environment.\n\n"
                "To fix this:\n"
                "1. Get an API key from: https://console.anthropic.com\n"
                "2. Set environment variable: export ANTHROPIC_API_KEY='your-key-here'\n"
                "3. Or add to your shell profile (~/.bashrc or ~/.zshrc):\n"
                "   export ANTHROPIC_API_KEY='your-key-here'\n\n"
                "Note: This will cost real money (~$0.001-0.003 per message).\n"
                "For learning, use demo_ai_agent instead (no cost, no API key needed)."
            )

        self._client = Anthropic(api_key=api_key)
        return self._client

    def complete(
        self,
        *,
        system: str,
        user: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        model: Optional[str] = None,
        schema: Optional[dict[str, Any]] = None,
    ) -> str:
        """
        Send a single system + user prompt to Claude and return the
        raw text of the assistant reply.

        ``schema``, a JSON schema, asks the API to constrain the reply to
        it (structured outputs). It is sent through ``extra_body`` so that
        it works with any ``anthropic`` library that has ``extra_body``,
        not only those that know ``output_config``.

        See `dissyslab.backends.base.Backend.complete` for the full
        contract.

        ``max_tokens``, ``temperature`` and ``model`` all fall back to
        the instance defaults set at ``__init__`` time when the caller
        passes ``None``. This is what makes named variants like
        ``anthropic_creative`` (temperature=1.0) and
        ``anthropic_precise`` (temperature=0.1) work: the variant is
        a factory entry that constructs the backend with a baked-in
        temperature, and ``nl_role``'s ``complete()`` call does not
        override it.
        """
        client = self._get_client()
        model_id = model or self._default_model
        request: dict[str, Any] = {
            "model": model_id,
            "max_tokens": (
                max_tokens if max_tokens is not None
                else self._default_max_tokens
            ),
            "system": system,
            "messages": [{"role": "user", "content": user}],
        }
        if schema is not None:
            request["extra_body"] = {
                "output_config": {"format": {"type": "json_schema", "schema": schema}}
            }
        if model_id not in _NO_TEMPERATURE:
            request["temperature"] = (
                temperature if temperature is not None
                else self._default_temperature
            )
        try:
            message = client.messages.create(**request)
        except Exception as exc:  # noqa: BLE001 - only the one refusal is handled
            if not _refuses_temperature(exc) or "temperature" not in request:
                raise
            # Newer models (claude-haiku-5-5, Nov 2026) reject the setting
            # outright. Ask again without it, and do not send it to this
            # model again in this run: the _creative and _precise variants
            # then behave like the plain name for it.
            _NO_TEMPERATURE.add(model_id)
            del request["temperature"]
            message = client.messages.create(**request)
        # The reply is the text block. Newer models (claude-haiku-5-5) put a
        # thinking block before it, so it is not always content[0].
        for block in message.content:
            if getattr(block, "type", "text") == "text":
                return block.text
        raise RuntimeError(
            f"Claude ({model_id}) returned no text, only "
            f"{', '.join(getattr(b, 'type', '?') for b in message.content) or 'nothing'} "
            f"(stop_reason: {getattr(message, 'stop_reason', None)})."
        )


#: Models that have refused a ``temperature``, so it is no longer sent to them.
_NO_TEMPERATURE: set[str] = set()


def _refuses_temperature(exc: Exception) -> bool:
    """A 400 from the API saying this model does not take ``temperature``."""
    return getattr(exc, "status_code", None) == 400 and "temperature" in str(exc)
