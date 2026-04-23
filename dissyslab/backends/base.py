# dissyslab/backends/base.py

"""
Backend Protocol — the interface between DisSysLab and the language model.

Every concrete backend implements a single `complete` method that takes
a system prompt and a user message and returns raw text. Callers
(`ai_agent`, the build-time compiler) are responsible for parsing JSON
or stripping markdown fences from the returned text.

This separation lets an SLM, OpenAI, Gemini, or any future provider
drop in as a new backend without touching `ai_agent.py`, the build-time
compiler, or any gallery office.

Student extension (for adding a new backend — e.g. a local SLM):

    from dissyslab.backends import Backend, register_backend

    class MySLMBackend:
        def complete(self, *, system, user,
                     max_tokens=1024, temperature=1.0,
                     model=None) -> str:
            # ... call your local model ...
            return text

    register_backend("my-slm", lambda: MySLMBackend())

Then set `DSL_BACKEND=my-slm` (in `.env` or the shell) and DisSysLab
uses it everywhere. See `anthropic_backend.py` in this package for a
reference implementation.
"""

from __future__ import annotations

from typing import Optional, Protocol, runtime_checkable


@runtime_checkable
class Backend(Protocol):
    """Text-completion interface. One method, no state required."""

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
        Return the model's text response.

        Args:
            system: System prompt — persona, instructions, output format.
            user:   User message — the actual query or spec.
            max_tokens: Upper bound on response length in tokens.
            temperature: Sampling temperature; 0.0 = deterministic.
            model: Optional model identifier. If None, the backend
                   picks its own default.

        Returns:
            Raw text response. Callers parse JSON or strip markdown
            fences as needed.

        Raises:
            Any exception raised by the underlying provider (missing
            key, rate limit, network error, malformed request). The
            CLI's `_explain_failure` helper triages common cases.
        """
        ...
