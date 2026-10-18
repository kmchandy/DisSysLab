"""Contracts on fields: what a field in ``in:`` or ``out:`` may hold.

Named values (``yes | no``) are older and tested in test_front_matter and
test_agents_reply. This file covers numbers, ranges and bounded text, and
``in:`` checked before a role is called. One case per rule.
"""

from __future__ import annotations

import pytest

from dissyslab.agents.reply import (
    Accepted,
    Rejected,
    check_annotator_reply,
    check_author_reply,
    check_incoming,
)
from dissyslab.office.frontmatter import Field, FrontMatterError, parse_front_matter


def fm(block: str):
    return parse_front_matter(f"---\n{block}\n---\n")


# ── Reading them ───────────────────────────────────────────────────────────


@pytest.mark.parametrize("written, field", [
    ("price (number)", Field("price", type="number")),
    ("price (number, 0..100000)", Field("price", type="number", low=0, high=100000)),
    ("score (0..10)", Field("score", type="number", low=0, high=10)),
    ("n (integer, >= 1)", Field("n", type="integer", low=1)),
    ("t (<= -2.5)", Field("t", type="number", high=-2.5)),
    ("reply (text)", Field("reply", type="text")),
    ("reply (text, at most 600 chars)", Field("reply", type="text", max_chars=600)),
    ("reply (at most 1 character)", Field("reply", type="text", max_chars=1)),
    # One word that is not a type is one named value, as it always was.
    ("verdict (yes)", Field("verdict", ("yes",))),
    ("level (3)", Field("level", ("3",))),
])
def test_what_a_field_may_hold_is_read(written, field):
    assert fm(f"out: {written}").outputs == (field,)


@pytest.mark.parametrize("written", [
    "price (number, 0..100000)",
    "n (integer, >= 1)",
    "t (number, <= -2.5)",
    "reply (text, at most 600 chars)",
    "verdict (publish | revise)",
    "plain",
])
def test_a_field_prints_as_it_is_written(written):
    """dsl roles and error messages show a field the way a student writes it."""
    assert str(fm(f"out: {written}").outputs[0]) == written


@pytest.mark.parametrize("written, message", [
    ("x (number, text)", "two types"),
    ("x (10..1)", "runs backwards"),
    ("x (text, 0..3)", "text cannot have a range"),
    ("x (number, at most 3 chars)", "a number has no length"),
    ("x (integer, 0.5..2)", "whole numbers"),
    ("x (between 1 and 2)", "not something a field can hold"),
])
def test_a_contract_that_makes_no_sense_is_an_error(written, message):
    with pytest.raises(FrontMatterError, match=message):
        fm(f"out: {written}")


def test_in_takes_the_same_contracts_and_still_lists_names():
    m = fm("in: amount (number, >= 0), title")
    assert m.inputs == ("amount", "title")
    assert m.input_fields == (Field("amount", type="number", low=0), Field("title"))


# ── Checking replies against out: ──────────────────────────────────────────


QUOTE = fm("out: price (number, 0..100000), reply (text, at most 20 chars)")


@pytest.mark.parametrize("reply", [
    {"price": 0, "reply": "ok"},
    {"price": 100000, "reply": "x" * 20},  # bounds are inclusive
    {"price": 62400.5, "reply": ""},
])
def test_a_reply_inside_its_contract_is_accepted(reply):
    assert isinstance(check_annotator_reply(reply, QUOTE, {}), Accepted)


@pytest.mark.parametrize("reply, reason", [
    ({"price": -1, "reply": "ok"}, "below its range (number, 0..100000)"),
    ({"price": 100001, "reply": "ok"}, "above its range"),
    ({"price": "62400", "reply": "ok"}, "is the text '62400', not a number"),
    ({"price": True, "reply": "ok"}, "not a number"),
    ({"price": None, "reply": "ok"}, "not a number"),
    ({"price": 1, "reply": "x" * 21}, "21 characters long; at most 20"),
    ({"price": 1, "reply": 7}, "not text"),
    ('{"price": NaN, "reply": "ok"}', "not a finite number"),
    ('{"price": Infinity, "reply": "ok"}', "not a finite number"),
])
def test_a_reply_outside_its_contract_is_rejected(reply, reason):
    result = check_annotator_reply(reply, QUOTE, {})
    assert isinstance(result, Rejected) and reason in result.reason, result


def test_an_integer_must_be_whole():
    m = fm("out: n (integer, >= 1)")
    assert isinstance(check_annotator_reply({"n": 3}, m, {}), Accepted)
    assert isinstance(check_annotator_reply({"n": 3.0}, m, {}), Accepted)  # JSON has one number type
    result = check_annotator_reply({"n": 2.5}, m, {})
    assert isinstance(result, Rejected) and "not a whole number" in result.reason


def test_an_author_reply_is_checked_the_same_way():
    m = fm("kind: author\nout: score (0..10)")
    result = check_author_reply([{"score": 3}, {"score": 11}], m)
    assert isinstance(result, Rejected) and result.reason.startswith("item 1:")


# ── Checking messages against in: ──────────────────────────────────────────


def test_a_message_that_fits_in_passes():
    m = fm("in: amount (number, >= 0), title")
    assert check_incoming({"amount": 20, "title": "t", "other": 1}, m) is None


@pytest.mark.parametrize("msg, reason", [
    ({"title": "t"}, "the message has no field 'amount'"),
    ({"amount": -5, "title": "t"}, "below its range"),
    ({"amount": "20", "title": "t"}, "not a number"),
])
def test_a_message_that_does_not_fit_in_is_refused(msg, reason):
    problem = check_incoming(msg, fm("in: amount (number, >= 0), title"))
    assert problem is not None and reason in problem


def test_without_in_every_message_passes():
    assert check_incoming({}, fm("out: x")) is None
