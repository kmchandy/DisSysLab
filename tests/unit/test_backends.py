# tests/unit/test_backends.py
"""
Unit tests for dissyslab.backends.

These cover the user-facing contract of the backend registry: name
resolution, the alias map, environment-variable lookup, and the
shared-singleton behavior. They do NOT exercise actual LLM calls —
the concrete AnthropicBackend / OllamaBackend / OpenRouterBackend
classes have their own integration tests.
"""

from __future__ import annotations

import os

import pytest

from dissyslab.backends import (
    AnthropicBackend,
    get_backend,
    register_backend,
)
import dissyslab.backends as backends_module


@pytest.fixture(autouse=True)
def _clear_backend_state(monkeypatch):
    """Wipe the cache and any DSL_BACKEND override between tests.

    The registry is intentionally NOT cleared — production code relies
    on the default ("anthropic", "ollama", "openrouter") entries being
    there for every call.
    """
    backends_module._CACHE.clear()
    monkeypatch.delenv("DSL_BACKEND", raising=False)
    yield
    backends_module._CACHE.clear()


def test_claude_alias_resolves_to_anthropic():
    """`DSL_BACKEND=claude` must select the Anthropic backend.

    Regression test for #147.2 — install.sh writes ``DSL_BACKEND=claude``
    into the user's shell rc, so the backend factory has to recognise
    that name. Without the alias, every Pat who picked "Claude" in the
    installer would hit ``Unknown backend: 'claude'`` on first run.
    """
    backend = get_backend("claude")
    assert isinstance(backend, AnthropicBackend)


def test_claude_alias_shares_anthropic_instance():
    """The alias must return the same singleton as the canonical name.

    Otherwise we'd have two AnthropicBackend instances doing duplicate
    setup work, and any backend-internal state (rate-limit counters,
    retry timers) would be split across two caches.
    """
    canonical = get_backend("anthropic")
    aliased = get_backend("claude")
    assert canonical is aliased


def test_env_var_with_alias_works(monkeypatch):
    """`DSL_BACKEND` env-var lookup must also honor aliases.

    This is the path that actually fires in production — install.sh
    writes ``export DSL_BACKEND=claude`` into ~/.zshrc, so the env-var
    branch of get_backend() is what every "Claude" installer hits.
    """
    monkeypatch.setenv("DSL_BACKEND", "claude")
    backend = get_backend()
    assert isinstance(backend, AnthropicBackend)


def test_case_insensitive_alias():
    """Alias keys are lowercased before lookup.

    Pat doesn't know whether the docs say "Claude" or "claude"; the
    install.sh banner shows it Title-cased while the env-var value is
    lowercase. Both forms have to work.
    """
    assert get_backend("Claude") is get_backend("claude")
    assert get_backend("CLAUDE") is get_backend("claude")


def test_unknown_backend_error_lists_aliases():
    """The Unknown-backend error includes alias names so users can find
    what to type when they typo the backend name."""
    with pytest.raises(ValueError) as exc_info:
        get_backend("not-a-real-backend")
    message = str(exc_info.value)
    assert "anthropic" in message
    assert "claude" in message


def test_register_backend_propagates_through_alias():
    """If a user re-registers "anthropic" with a custom factory, the
    "claude" alias must pick up the new factory automatically.

    This is the reason we use an alias map rather than duplicating
    the factory under both names in the registry.
    """

    class FakeAnthropic(AnthropicBackend):
        """Stand-in subclass — type-checked instance comparison only."""

    register_backend("anthropic", lambda: FakeAnthropic.__new__(FakeAnthropic))
    try:
        # The alias should resolve to the newly-registered factory.
        aliased = get_backend("claude")
        canonical = get_backend("anthropic")
        assert aliased is canonical
        assert type(aliased) is FakeAnthropic
    finally:
        # Restore the default Anthropic factory so other tests don't
        # see the FakeAnthropic instance.
        register_backend("anthropic", lambda: AnthropicBackend(temperature=0.7))


# ── Named-variant registry ────────────────────────────────────────────


def test_named_variants_have_distinct_temperatures():
    """The three-tier _creative / bare / _precise convention must give
    measurably different sampling temperatures.

    Regression test for the L1.5 design: a user picks the persona name
    rather than a number, and the registry encodes the number behind
    the scenes. If a variant ever collapses to the same temperature as
    the bare name, the convention has lost its meaning.
    """
    for prefix in ("anthropic", "ollama", "openrouter"):
        bare = get_backend(prefix)
        creative = get_backend(f"{prefix}_creative")
        precise = get_backend(f"{prefix}_precise")
        # All three are distinct instances with distinct stored temps.
        assert bare._default_temperature == 0.7
        assert creative._default_temperature == 1.0
        assert precise._default_temperature == 0.1
        assert bare is not creative
        assert bare is not precise
        assert creative is not precise


def test_claude_qwen_aliases_track_variants():
    """The Pat-facing aliases (claude, qwen) get the full three-tier
    treatment, so office.md can read naturally:

        Claude's AI is claude_creative.
        Qwen's AI is qwen_precise.

    This regression test pins each alias to the canonical variant
    that backs it.
    """
    pairs = [
        ("claude",           "anthropic"),
        ("claude_creative",  "anthropic_creative"),
        ("claude_precise",   "anthropic_precise"),
        ("qwen",             "ollama"),
        ("qwen_creative",    "ollama_creative"),
        ("qwen_precise",     "ollama_precise"),
    ]
    for alias, canonical in pairs:
        assert get_backend(alias) is get_backend(canonical)


def test_backend_constructor_temperature_reaches_complete(monkeypatch):
    """Constructing AnthropicBackend(temperature=0.1) must result in
    that temperature appearing in the API call. This is the contract
    the L1.5 design rests on: instance state -> complete() arg ->
    upstream API.

    We mock the Anthropic client so no network call fires; the test
    just inspects the kwargs the backend passes to ``messages.create``.
    """
    captured = {}

    class _FakeMessages:
        def create(self, **kwargs):
            captured.update(kwargs)
            # Return an object whose .content[0].text the backend can read.
            class _C:
                text = "ok"
            class _M:
                content = [_C()]
            return _M()

    class _FakeClient:
        def __init__(self):
            self.messages = _FakeMessages()

    backend = AnthropicBackend(temperature=0.1, max_tokens=512)
    monkeypatch.setattr(backend, "_get_client", lambda: _FakeClient())
    backend.complete(system="s", user="u")

    assert captured["temperature"] == 0.1
    assert captured["max_tokens"] == 512


def test_backend_per_call_overrides_instance_temperature(monkeypatch):
    """Per-call ``temperature=`` to complete() must override the
    instance default. Power users dropping into a .py role file can
    still pin a specific temperature without going through the
    registry.
    """
    captured = {}

    class _FakeMessages:
        def create(self, **kwargs):
            captured.update(kwargs)
            class _C: text = "ok"
            class _M: content = [_C()]
            return _M()

    class _FakeClient:
        def __init__(self):
            self.messages = _FakeMessages()

    backend = AnthropicBackend(temperature=0.1)
    monkeypatch.setattr(backend, "_get_client", lambda: _FakeClient())
    backend.complete(system="s", user="u", temperature=0.9)

    assert captured["temperature"] == 0.9
