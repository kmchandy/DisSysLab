# examples/custom_backend/mock_backend.py
"""
Mock backend — proves the Backend Protocol works end-to-end without
calling any external LLM.

Useful for:
  - Testing that DSL_BACKEND_MODULE registration is wired correctly.
  - Showing extension authors the smallest possible Backend
    implementation (under 30 lines including docs).

Not useful for:
  - Actually running offices — the analyst won't analyze anything,
    because the response is canned. Use a real backend (Anthropic,
    OpenAI, Gemini, Ollama) for real work. See docs/ADD_A_BACKEND.md.

To use:
    export DSL_BACKEND_MODULE=mock_backend
    export DSL_BACKEND=mock
    python -c "from dissyslab.backends import get_backend; \
               print(get_backend().complete(system='hi', user='hello'))"
"""

from typing import Optional

from dissyslab.backends import register_backend


class MockBackend:
    """Backend that returns a canned, deterministic response."""

    def complete(
        self,
        *,
        system: str,
        user: str,
        max_tokens: int = 1024,
        temperature: float = 1.0,
        model: Optional[str] = None,
    ) -> str:
        # Echo input lengths and a snippet of the user message so it's
        # obvious in logs that the mock is in use, not the real LLM.
        return (
            f"[mock backend] received system={len(system)} chars, "
            f"user={len(user)} chars. user-msg[:80]={user[:80]!r}"
        )


# Register at import time. dissyslab will import this module if you
# set DSL_BACKEND_MODULE=mock_backend before running `dsl run`.
register_backend("mock", lambda: MockBackend())
