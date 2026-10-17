# docs/recipes/add-a-backend/mock_backend.py
"""
Mock backend — proves the Backend Protocol works end-to-end without
calling any external LLM.

Useful for:
  - Testing that DSL_BACKEND_MODULE registration is wired correctly.
  - Showing extension authors the smallest possible Backend
    implementation (under 30 lines including docs).

Not useful for real work: every reply is the same text, which is not
JSON, so every English role that uses it fails -- which is itself worth
seeing once (README.md, step 2).

To use, from this folder:
    python -c "import mock_backend; from dissyslab.backends import get_backend; \
               print(get_backend('mock').complete(system='hi', user='hello'))"
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


# Register at import time. `dsl` imports this module when
# DSL_BACKEND_MODULE=mock_backend is set and the folder is on PYTHONPATH.
register_backend("mock", lambda: MockBackend())
