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


# ── which model, and is it still served (dsl doctor .) ───────────────────

class _Catalogue:
    def __init__(self, ids, status=200):
        self.status_code = status
        self._ids = ids

    def json(self):
        return {"data": [{"id": i} for i in self._ids]}


def test_the_default_is_used_unless_openrouter_model_is_set(monkeypatch):
    monkeypatch.delenv("OPENROUTER_MODEL", raising=False)
    assert openrouter_backend.configured_model() == (openrouter_backend.DEFAULT_MODEL, "the default")
    monkeypatch.setenv("OPENROUTER_MODEL", "google/gemma-3-4b-it")
    assert openrouter_backend.configured_model() == ("google/gemma-3-4b-it", "OPENROUTER_MODEL")
    assert OpenRouterBackend()._resolve_model(None) == "google/gemma-3-4b-it"


def test_model_listed_asks_the_catalogue_and_says_when_it_cannot(monkeypatch):
    monkeypatch.setattr(openrouter_backend.requests, "get",
                        lambda *a, **k: _Catalogue(["a/one", "b/two:free"]))
    assert openrouter_backend.model_listed("b/two:free") is True
    assert openrouter_backend.model_listed("qwen/qwen-2.5-7b-instruct") is False

    def down(*a, **k):
        raise openrouter_backend.requests.ConnectionError("offline")
    monkeypatch.setattr(openrouter_backend.requests, "get", down)
    assert openrouter_backend.model_listed("a/one") is None


def _doctor(tmp_path, monkeypatch, capsys, listed_ids, model=None):
    import shutil
    from pathlib import Path

    from dissyslab import cli
    gallery = Path(cli.__file__).parent / "gallery" / "car_dealer"
    office = tmp_path / "lab1"
    shutil.copytree(gallery, office, ignore=shutil.ignore_patterns("__pycache__"))
    monkeypatch.setenv("DSL_BACKEND", "openrouter")
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test")
    if model:
        monkeypatch.setenv("OPENROUTER_MODEL", model)
    else:
        monkeypatch.delenv("OPENROUTER_MODEL", raising=False)
    if listed_ids is None:
        def down(*a, **k):
            raise openrouter_backend.requests.ConnectionError("offline")
        monkeypatch.setattr(openrouter_backend.requests, "get", down)
    else:
        monkeypatch.setattr(openrouter_backend.requests, "get", lambda *a, **k: _Catalogue(listed_ids))
    ok = cli._doctor_office(office)
    return ok, capsys.readouterr().out


def test_doctor_says_not_ready_when_openrouter_has_withdrawn_the_model(tmp_path, monkeypatch, capsys):
    ok, out = _doctor(tmp_path, monkeypatch, capsys, ["meta-llama/llama-3.1-8b-instruct"],
                      model="qwen/qwen-2.5-7b-instruct")
    assert not ok
    assert "[FAIL] OpenRouter does not list qwen/qwen-2.5-7b-instruct (OPENROUTER_MODEL)" in out
    assert "export OPENROUTER_MODEL=" in out
    assert "Not ready to run: OpenRouter does not serve qwen/qwen-2.5-7b-instruct." in out


def test_doctor_names_the_default_when_it_is_served(tmp_path, monkeypatch, capsys):
    ok, out = _doctor(tmp_path, monkeypatch, capsys, [openrouter_backend.DEFAULT_MODEL])
    assert ok and "Ready to run." in out
    assert f"[OK] OpenRouter serves {openrouter_backend.DEFAULT_MODEL} (the default;" in out


def test_doctor_offline_does_not_block_the_run(tmp_path, monkeypatch, capsys):
    ok, out = _doctor(tmp_path, monkeypatch, capsys, None)
    assert ok and "[--] could not reach OpenRouter" in out


def test_doctor_does_not_ask_openrouter_on_the_default_backend(tmp_path, monkeypatch, capsys):
    def boom(*a, **k):
        raise AssertionError("dsl doctor asked OpenRouter on the anthropic backend")
    monkeypatch.setattr(openrouter_backend.requests, "get", boom)
    import shutil
    from pathlib import Path

    from dissyslab import cli
    office = tmp_path / "lab1"
    shutil.copytree(Path(cli.__file__).parent / "gallery" / "car_dealer", office,
                    ignore=shutil.ignore_patterns("__pycache__"))
    monkeypatch.delenv("DSL_BACKEND", raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    assert cli._doctor_office(office)
    assert "OpenRouter" not in capsys.readouterr().out


def test_every_place_that_names_the_default_names_the_same_one():
    """install.sh writes the default into the student's shell rc file; a stale
    one there overrides the library's, which is how a withdrawn model lives on."""
    import re
    from pathlib import Path
    repo = Path(__file__).resolve().parents[2]
    default = openrouter_backend.DEFAULT_MODEL
    install = (repo / "install.sh").read_text(encoding="utf-8")
    assert re.search(r'^OPENROUTER_DEFAULT_MODEL="([^"]+)"', install, re.M).group(1) == default
    assert f"default `{default}`" in (repo / "docs" / "LANGUAGE_MODELS.md").read_text(encoding="utf-8")
    assert f"OPENROUTER_MODEL={default}" in (repo / "README.pypi.md").read_text(encoding="utf-8")
