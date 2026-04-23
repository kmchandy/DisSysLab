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
from typing import Optional

from anthropic import Anthropic


DEFAULT_MODEL = "claude-sonnet-4-5"


class AnthropicBackend:
    """Concrete Backend backed by the Anthropic Claude API."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ) -> None:
        """
        Args:
            api_key: Anthropic API key. If None, read from
                     ANTHROPIC_API_KEY at first `complete` call.
            model:   Default model to use when `complete(model=None)`.
                     If None, uses DEFAULT_MODEL.
        """
        self._api_key = api_key
        self._default_model = model or DEFAULT_MODEL
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
        max_tokens: int = 1024,
        temperature: float = 1.0,
        model: Optional[str] = None,
    ) -> str:
        """
        Send a single system + user prompt to Claude and return the
        raw text of the assistant reply.

        See `dissyslab.backends.base.Backend.complete` for the full
        contract.
        """
        client = self._get_client()
        message = client.messages.create(
            model=model or self._default_model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system,
            messages=[
                {"role": "user", "content": user},
            ],
        )
        return message.content[0].text
