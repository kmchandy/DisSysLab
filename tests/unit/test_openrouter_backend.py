"""OpenRouter's catalogue changes under us: a withdrawn model must produce an
error that says how to choose another, not only an HTTP status.

qwen/qwen-2.5-7b-instruct, the default, was withdrawn in November 2026 and
the first anyone knew was a 404 in the middle of a lab run.
"""

from __future__ import annotations

import pytest

from dissyslab.backends import openrouter_backend
from dissyslab.backends.openrouter_backend import OpenRouterBackend


class _Response:
    def __init__(self, status_code: int, text: str) -> None:
        self.status_code = status_code
        self.text = text


def test_a_withdrawn_model_says_how_to_choose_another(monkeypatch):
    gone = ('{"error":{"message":"some/model is no longer available on OpenRouter: '
            'no provider serves this model anymore.","code":404}}')
    monkeypatch.setattr(openrouter_backend.requests, "post",
                        lambda *a, **k: _Response(404, gone))
    backend = OpenRouterBackend(api_key="sk-or-test", model="some/model")
    with pytest.raises(RuntimeError) as err:
        backend.complete(system="s", user="u")
    said = str(err.value)
    assert "'some/model'" in said
    assert "export OPENROUTER_MODEL=" in said
    assert "https://openrouter.ai/models" in said
    assert "no longer available" in said  # OpenRouter's own words are kept


def test_other_http_errors_still_show_openrouters_body(monkeypatch):
    monkeypatch.setattr(openrouter_backend.requests, "post",
                        lambda *a, **k: _Response(429, "rate limited"))
    backend = OpenRouterBackend(api_key="sk-or-test", model="some/model")
    with pytest.raises(RuntimeError, match="OpenRouter HTTP 429: rate limited"):
        backend.complete(system="s", user="u")
