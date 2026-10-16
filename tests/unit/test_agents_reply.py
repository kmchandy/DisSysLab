"""Checking a role's reply (spec section 4.5), one case per rule."""

from __future__ import annotations

import pytest

from dissyslab.agents.reply import (
    Accepted,
    Rejected,
    check_annotator_reply,
    check_author_reply,
    parse_reply,
)
from dissyslab.office.frontmatter import parse_front_matter


def fm(block: str):
    return parse_front_matter(f"---\n{block}\n---\n")


ARTICLE = {"title": "Brazil votes", "text": "...", "url": "u"}
ON_TOPIC = fm("out: on_topic (yes | no)")


# ── Parsing ────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("text", [
    '{"a": 1}',
    '  {"a": 1}\n',
    '```json\n{"a": 1}\n```',
    '```\n{"a": 1}\n```',
])
def test_one_json_value_with_at_most_one_fence(text):
    assert parse_reply(text) == {"a": 1}


@pytest.mark.parametrize("text", [
    'Sure! {"a": 1}',
    '```json\n{"a": 1}\n```\n```json\n{"b": 2}\n```',
    "",
])
def test_anything_else_is_not_json(text):
    with pytest.raises(ValueError):
        parse_reply(text)


def test_a_python_reply_is_not_parsed():
    assert parse_reply({"a": 1}) == {"a": 1}


# ── Annotators ─────────────────────────────────────────────────────────────


def test_an_annotator_adds_its_fields():
    result = check_annotator_reply('{"on_topic": "yes"}', ON_TOPIC, ARTICLE)
    assert result == Accepted(({**ARTICLE, "on_topic": "yes"},))


def test_undeclared_fields_are_dropped_and_named():
    result = check_annotator_reply(
        '{"on_topic": "yes", "reason": "Brazil", "confidence": 0.9}', ON_TOPIC, ARTICLE)
    assert result == Accepted(({**ARTICLE, "on_topic": "yes"},), ("reason", "confidence"))


@pytest.mark.parametrize("reply, reason", [
    ('{"topic": "yes"}', "the reply has no field 'on_topic'."),
    ('{"on_topic": "maybe"}', "'on_topic' is 'maybe', which is not one of yes, no."),
    ('{"on_topic": "Yes"}', "'on_topic' is 'Yes', which is not one of yes, no (closest: 'yes')."),
    ('["yes"]', "an annotator returns one JSON object, not list."),
    ("I think yes.", "the reply is not JSON."),
])
def test_an_annotator_reply_that_does_not_fit(reply, reason):
    assert check_annotator_reply(reply, ON_TOPIC, ARTICLE) == Rejected(reason)


def test_an_annotator_only_adds():
    result = check_annotator_reply('{"on_topic": "yes", "title": "Changed"}',
                                   fm("out: on_topic (yes | no), title"), ARTICLE)
    assert isinstance(result, Rejected) and "would change 'title'" in result.reason
    # The same value again is not a change.
    same = check_annotator_reply('{"on_topic": "yes", "title": "Brazil votes"}',
                                 fm("out: on_topic (yes | no), title"), ARTICLE)
    assert isinstance(same, Accepted)


def test_without_out_nothing_is_checked_or_dropped():
    result = check_annotator_reply('{"anything": 1}', fm("emits: x"), ARTICLE)
    assert result == Accepted(({**ARTICLE, "anything": 1},))


def test_booleans_and_numbers_compare_by_written_form():
    flag = fm("out: ok (true | false), n (1 | 2)")
    assert isinstance(check_annotator_reply({"ok": True, "n": 2}, flag, {}), Accepted)
    assert isinstance(check_annotator_reply({"ok": "yes", "n": 2}, flag, {}), Rejected)


def test_a_python_annotator_reply_is_checked_the_same_way():
    clerk = fm("out: clerk_decision (approve | escalate)")
    assert check_annotator_reply({"clerk_decision": "approve"}, clerk, {"amount": 20}) == \
        Accepted(({"amount": 20, "clerk_decision": "approve"},))
    assert isinstance(check_annotator_reply({"clerk_decision": "ok"}, clerk, {}), Rejected)


# ── Authors ────────────────────────────────────────────────────────────────

REFEREE = fm(
    "kind: author\n"
    "out: next (finish | continue), problem_id\n"
    "out if next is finish: final_answer\n"
    "out if next is continue: round")


def test_an_author_sends_each_object():
    result = check_author_reply(
        [{"next": "continue", "problem_id": "p1", "round": 1},
         {"next": "finish", "problem_id": "p2", "final_answer": "A", "note": "x"}],
        REFEREE)
    assert result == Accepted(
        ({"next": "continue", "problem_id": "p1", "round": 1},
         {"next": "finish", "problem_id": "p2", "final_answer": "A"}),
        ("note",))


def test_the_empty_list_sends_nothing():
    assert check_author_reply("[]", REFEREE) == Accepted(())


@pytest.mark.parametrize("reply, reason", [
    ({"next": "finish"}, "an author returns a JSON list of objects, not dict."),
    (["x"], "item 0 of the reply is str, not an object."),
    ([{"next": "finish", "problem_id": "p"}], "item 0: the reply has no field 'final_answer'."),
    ([{"next": "continue", "problem_id": "p"}], "item 0: the reply has no field 'round'."),
    ([{"next": "stop", "problem_id": "p"}],
     "item 0: 'next' is 'stop', which is not one of finish, continue."),
])
def test_an_author_reply_that_does_not_fit(reply, reason):
    assert check_author_reply(reply, REFEREE) == Rejected(reason)


def test_same_as_in_passes_objects_unchanged():
    dedup = fm("kind: author\nout: same as in")
    assert check_author_reply([ARTICLE], dedup) == Accepted((ARTICLE,))
    assert check_author_reply([], dedup) == Accepted(())
