# dissyslab/backends/__init__.py

"""
Backend registry.

Exposes:
  - `Backend`            — the Protocol every backend implements.
  - `AnthropicBackend`   — the default concrete backend.
  - `get_backend(name)`  — lazy singleton factory.
  - `register_backend(name, factory)` — extension hook for new
                                         backends (SLM, OpenAI, etc.).

The active backend is chosen by the `DSL_BACKEND` environment
variable. If unset, "anthropic" is used. Students never set this;
the happy path is unchanged.
"""

from __future__ import annotations

import os
from typing import Callable, Dict, Optional

from dissyslab.backends.base import Backend
from dissyslab.backends.anthropic_backend import AnthropicBackend
from dissyslab.backends.ollama_backend import OllamaBackend
from dissyslab.backends.openrouter_backend import OpenRouterBackend

__all__ = [
    "Backend",
    "AnthropicBackend",
    "OllamaBackend",
    "OpenRouterBackend",
    "get_backend",
    "register_backend",
]


# Factories produce a backend instance on demand. A factory (not an
# instance) is registered so that construction — which may touch the
# environment or network — is deferred until first use.
#
# Named-variant convention
# ------------------------
#
# For every backend, three registry entries are provided:
#
# * Bare name (e.g. ``anthropic``) — a *balanced* default
#   (temperature 0.7).
# * ``<name>_creative`` (e.g. ``anthropic_creative``) — high
#   temperature (1.0); favours novelty / variance.
# * ``<name>_precise`` (e.g. ``anthropic_precise``) — low
#   temperature (0.1); favours determinism.
#
# This lets office.md select the LLM persona in plain English —
# ``Claude's AI is anthropic_creative.`` — without the office writer
# having to think about numerical temperatures. Power users who want
# a specific temperature can still construct the backend directly in
# a .py role file via ``AnthropicBackend(temperature=0.4)``.
_REGISTRY: Dict[str, Callable[[], Backend]] = {
    # Anthropic / Claude
    "anthropic":           lambda: AnthropicBackend(temperature=0.7),
    "anthropic_creative":  lambda: AnthropicBackend(temperature=1.0),
    "anthropic_precise":   lambda: AnthropicBackend(temperature=0.1),
    # Ollama (local — typically Qwen)
    "ollama":              lambda: OllamaBackend(temperature=0.7),
    "ollama_creative":     lambda: OllamaBackend(temperature=1.0),
    "ollama_precise":      lambda: OllamaBackend(temperature=0.1),
    # OpenRouter (cloud — typically Qwen)
    "openrouter":          lambda: OpenRouterBackend(temperature=0.7),
    "openrouter_creative": lambda: OpenRouterBackend(temperature=1.0),
    "openrouter_precise":  lambda: OpenRouterBackend(temperature=0.1),
}

# Aliases let multiple user-facing names resolve to the same registered
# backend. Pat types the product name ("claude"), install.sh writes
# DSL_BACKEND=claude into ~/.zshrc, and we resolve it to "anthropic"
# here. Adding an alias is cheaper and safer than duplicating the
# factory — re-registering "anthropic" automatically updates "claude"
# too. Keys are lowercased before lookup.
#
# The Pat-facing model names (claude, qwen) each get the same
# three-tier creative / bare / precise treatment as the underlying
# backend, so ``Qwen's AI is qwen_creative.`` works in office.md.
_ALIASES: Dict[str, str] = {
    # Claude (= anthropic)
    "claude":           "anthropic",
    "claude_creative":  "anthropic_creative",
    "claude_precise":   "anthropic_precise",
    # Qwen (= ollama by default; users running Qwen via OpenRouter
    # should write openrouter / openrouter_creative / openrouter_precise
    # directly).
    "qwen":             "ollama",
    "qwen_creative":    "ollama_creative",
    "qwen_precise":     "ollama_precise",
}

# One lazily-constructed singleton per backend name. Cleared when a
# name is re-registered (useful in tests).
_CACHE: Dict[str, Backend] = {}


def register_backend(name: str, factory: Callable[[], Backend]) -> None:
    """
    Register a new backend under `name`.

    Args:
        name:    Identifier used in `DSL_BACKEND` or
                 `get_backend(name)` calls. Case-insensitive.
        factory: Zero-arg callable returning a Backend instance.
                 Called lazily on first `get_backend(name)`.

    Example:
        >>> from dissyslab.backends import register_backend
        >>> register_backend("my-slm", lambda: MySLMBackend())
    """
    key = name.lower()
    _REGISTRY[key] = factory
    _CACHE.pop(key, None)


def get_backend(name: Optional[str] = None) -> Backend:
    """
    Return the active backend instance.

    Resolution order:
      1. Explicit `name` argument (if given).
      2. `DSL_BACKEND` environment variable.
      3. Default: "anthropic".

    The same instance is returned on subsequent calls with the same
    name (lazy singleton per name).

    Raises:
        ValueError: if the requested backend name is not registered.
    """
    key = (name or os.environ.get("DSL_BACKEND") or "anthropic").lower()
    # Resolve aliases (e.g. "claude" -> "anthropic") so the cache and
    # registry only ever see canonical names.
    key = _ALIASES.get(key, key)

    if key in _CACHE:
        return _CACHE[key]

    if key not in _REGISTRY:
        # Show both canonical names and aliases so the error message
        # matches what users typed.
        known_canonical = sorted(_REGISTRY)
        known_aliases = sorted(_ALIASES)
        known = ", ".join(known_canonical + known_aliases) or "(none)"
        raise ValueError(
            f"Unknown backend: {key!r}. Known backends: {known}.\n"
            f"Set DSL_BACKEND to one of the known names, or register "
            f"a new backend with register_backend()."
        )

    backend = _REGISTRY[key]()
    _CACHE[key] = backend
    return backend
