"""An English role's reply shape, enforced by the model's API.

Lab 1, 16 Nov 2026: Haiku 5.5 answered nine customers as {"reply": ...}
and the tenth in plain text. The contract refused it, the refusal stopped
the office, and seven customers got no answer. A slip in the *shape* of a
reply is not what a contract is for, so when every out: field says what it
holds, the shape goes to the API as a JSON schema (Anthropic's structured
outputs) and the model cannot answer in any other shape.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dissyslab.agents import english
from dissyslab.agents.english import reply_schema
from dissyslab.backends import anthropic_backend
from dissyslab.backends.anthropic_backend import AnthropicBackend
from dissyslab.office.frontmatter import parse_front_matter, read_front_matter

REPO = Path(__file__).resolve().parents[2]


def fm(out_line: str, extra: str = ""):
    return parse_front_matter(f"---\nin: text\n{extra}out: {out_line}\n---\nDo it.\n")


def test_lab_1s_sal_gets_a_schema_for_its_reply_and_its_sale():
    sal = read_front_matter(REPO / "dissyslab" / "gallery" / "car_dealer" / "roles" / "salesperson.md")
    assert reply_schema(sal) == {
        "type": "object",
        "properties": {
            "reply": {"type": "string"},
            "sale": {"type": "string", "enum": ["yes", "no"]},
            "vehicle": {"type": "string",
                        "enum": ["tahoe", "silverado", "equinox", "trax", "malibu", "none"]},
            "price": {"type": "number"},
        },
        "required": ["reply", "sale", "vehicle", "price"], "additionalProperties": False}


def test_values_numbers_and_text_become_the_schema_and_bounds_stay_with_the_contract():
    schema = reply_schema(fm("reply (text, at most 600 chars), book (yes | no), "
                             "price (number, >= 0), count (integer, 0..10)"))
    assert schema["properties"] == {
        "reply": {"type": "string"}, "book": {"type": "string", "enum": ["yes", "no"]},
        "price": {"type": "number"}, "count": {"type": "integer"}}
    assert schema["required"] == ["reply", "book", "price", "count"]


@pytest.mark.parametrize("out_line", ["entities", "reply (text), note", "same as in",
                                      "stars (1 | 2 | 3)"])
def test_no_schema_when_a_field_may_hold_anything(out_line):
    assert reply_schema(fm(out_line)) is None


def test_no_schema_without_an_out_line():
    assert reply_schema(parse_front_matter("---\nin: text\n---\nDo it.\n")) is None


class _Recorder:
    def __init__(self, supports: bool) -> None:
        self.supports_schema = supports
        self.calls: list[dict] = []

    def complete(self, **kwargs):
        self.calls.append(kwargs)
        return '{"reply": "hi"}'


@pytest.mark.parametrize("supports", [True, False])
def test_the_schema_goes_only_to_a_backend_that_can_enforce_it(monkeypatch, supports):
    backend = _Recorder(supports)
    monkeypatch.setattr(english, "get_backend", lambda ai: backend)
    english.english_call(fm("reply (text)"))({"text": "hello"})
    (call,) = backend.calls
    assert ("schema" in call) == supports
    if supports:
        assert call["schema"]["properties"] == {"reply": {"type": "string"}}


def test_a_backend_that_says_nothing_about_schemas_gets_none(monkeypatch):
    class Old:
        def complete(self, *, system, user, max_tokens=1024, temperature=1.0, model=None):
            return '{"reply": "hi"}'
    monkeypatch.setattr(english, "get_backend", lambda ai: Old())
    assert english.english_call(fm("reply (text)"))({"text": "hello"}) == '{"reply": "hi"}'


# ── the Anthropic backend ─────────────────────────────────────────────────

class _Block:
    type = "text"

    def __init__(self, text):
        self.text = text


class _Client:
    def __init__(self):
        self.kwargs = None
        self.messages = self

    def create(self, **kwargs):
        self.kwargs = kwargs
        return type("M", (), {"content": [_Block('{"reply": "hi"}')]})()


def test_anthropic_sends_the_schema_as_output_config(monkeypatch):
    backend = AnthropicBackend(api_key="sk-ant-test")
    backend._client = client = _Client()
    schema = reply_schema(fm("reply (text)"))
    assert backend.complete(system="s", user="u", schema=schema) == '{"reply": "hi"}'
    assert client.kwargs["extra_body"] == {
        "output_config": {"format": {"type": "json_schema", "schema": schema}}}
    backend.complete(system="s", user="u")
    assert "extra_body" not in client.kwargs


def test_the_default_is_haiku_and_anthropic_model_overrides_it(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_MODEL", raising=False)
    backend = AnthropicBackend(api_key="sk-ant-test")
    backend._client = client = _Client()
    backend.complete(system="s", user="u")
    assert client.kwargs["model"] == anthropic_backend.DEFAULT_MODEL == "claude-haiku-5-5"
    monkeypatch.setenv("ANTHROPIC_MODEL", "claude-sonnet-5-5")
    backend = AnthropicBackend(api_key="sk-ant-test")
    backend._client = client = _Client()
    backend.complete(system="s", user="u")
    assert client.kwargs["model"] == "claude-sonnet-5-5"


class _NoTemperatureClient(_Client):
    """Lab 1, 16 Nov 2026: claude-haiku-5-5 answered every call with
    400 "`temperature` is deprecated for this model"."""

    def __init__(self):
        super().__init__()
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if "temperature" in kwargs:
            err = Exception("Error code: 400 - `temperature` is deprecated for this model.")
            err.status_code = 400
            raise err
        return super().create(**kwargs)


def test_a_model_that_refuses_temperature_is_asked_again_without_it(monkeypatch):
    monkeypatch.setattr(anthropic_backend, "_NO_TEMPERATURE", set())
    backend = AnthropicBackend(api_key="sk-ant-test", model="claude-new", temperature=0.1)
    backend._client = client = _NoTemperatureClient()
    schema = reply_schema(fm("reply (text)"))
    assert backend.complete(system="s", user="u", schema=schema) == '{"reply": "hi"}'
    assert [("temperature" in c) for c in client.calls] == [True, False]
    assert client.calls[1]["extra_body"]["output_config"]["format"]["schema"] == schema
    backend.complete(system="s", user="u")          # remembered: one call, no temperature
    assert [("temperature" in c) for c in client.calls] == [True, False, False]


def test_other_errors_are_not_retried(monkeypatch):
    monkeypatch.setattr(anthropic_backend, "_NO_TEMPERATURE", set())

    class Broken(_Client):
        def create(self, **kwargs):
            err = Exception("Error code: 400 - max_tokens is too large")
            err.status_code = 400
            raise err
    backend = AnthropicBackend(api_key="sk-ant-test")
    backend._client = Broken()
    with pytest.raises(Exception, match="max_tokens"):
        backend.complete(system="s", user="u")
    assert anthropic_backend._NO_TEMPERATURE == set()


class _Thinking:
    """A block with no .text, as the SDK's ThinkingBlock has none."""
    type = "thinking"


def test_the_text_block_is_the_reply_even_after_a_thinking_block():
    """Lab 1, 16 Nov 2026: claude-haiku-5-5 put a ThinkingBlock first, and
    reading content[0].text raised AttributeError on every customer."""
    class Thinks(_Client):
        def create(self, **kwargs):
            return type("M", (), {"content": [_Thinking(), _Block('{"reply": "hi"}')]})()
    backend = AnthropicBackend(api_key="sk-ant-test")
    backend._client = Thinks()
    assert backend.complete(system="s", user="u") == '{"reply": "hi"}'


def test_only_thinking_says_so():
    class OnlyThinks(_Client):
        def create(self, **kwargs):
            return type("M", (), {"content": [_Thinking()], "stop_reason": "max_tokens"})()
    backend = AnthropicBackend(api_key="sk-ant-test")
    backend._client = OnlyThinks()
    with pytest.raises(RuntimeError, match=r"no text, only thinking \(stop_reason: max_tokens\)"):
        backend.complete(system="s", user="u")


def test_the_docs_name_the_default():
    docs = (REPO / "docs" / "LANGUAGE_MODELS.md").read_text(encoding="utf-8")
    assert f"`{anthropic_backend.DEFAULT_MODEL}`" in docs
