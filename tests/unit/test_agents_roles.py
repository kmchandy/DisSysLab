"""Role agents running in a real network: English and Python, annotator and author.

Each test builds a small network by hand -- a list source, one role agent,
a collecting sink -- and runs it to completion with the frozen runtime.
English roles use a scripted model registered for the test, so nothing
leaves the machine.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from dissyslab.agents.english import english_call, prompt_for, user_message
from dissyslab.agents.python_role import RoleLoadError, python_call
from dissyslab.agents.role_agent import AnnotatorAgent, AuthorAgent, role_agent
from dissyslab.backends import register_backend
from dissyslab.blocks import Sink, Source
from dissyslab.network import Network
from dissyslab.office.frontmatter import parse_front_matter, read_front_matter


def run_through(agent, items):
    """Run items -> agent -> collector; return (collected messages, network)."""
    it = iter(items)
    out: list = []
    net = Network(
        blocks={"src": Source(fn=lambda: next(it, None), name="src"), "role": agent,
                "sink": Sink(fn=out.append, name="sink")},
        connections=[("src", "out_", "role", "in_"), ("role", "out_", "sink", "in_")],
    )
    net.run_network()
    return out, net


class Scripted:
    """A model that answers each prompt from a function of the user message."""

    def __init__(self, answer):
        self.answer = answer
        self.calls: list[tuple[str, str]] = []

    def complete(self, *, system, user, max_tokens=1024, temperature=1.0, model=None):
        self.calls.append((system, user))
        return self.answer(json.loads(user))


TOPIC = parse_front_matter(
    "---\nin: title\nout: on_topic (yes | no)\n---\n"
    "Decide whether the article is about the Americas.\n"
    'Return only a JSON object with one field, "on_topic".\n')


# ── English roles ──────────────────────────────────────────────────────────


def test_the_prompt_is_the_text_and_the_message_is_json():
    assert prompt_for(TOPIC) == (
        "Decide whether the article is about the Americas.\n"
        'Return only a JSON object with one field, "on_topic".\n')
    assert user_message({"title": "Brazil"}) == '{"title": "Brazil"}'


def test_an_english_annotator_end_to_end():
    model = Scripted(lambda m: json.dumps(
        {"on_topic": "yes" if "Brazil" in m["title"] else "no", "why": "x"}))
    register_backend("scripted_test", lambda: model)
    agent = role_agent("Felix", english_call(TOPIC, ai="scripted_test"), TOPIC)
    assert isinstance(agent, AnnotatorAgent)
    out, net = run_through(agent, [{"title": "Brazil votes"}, {"title": "Tokyo rains"}])
    assert out == [{"title": "Brazil votes", "on_topic": "yes"},
                   {"title": "Tokyo rains", "on_topic": "no"}]
    # Exactly the role's text, nothing appended; the message as JSON.
    assert model.calls[0] == (prompt_for(TOPIC), '{"title": "Brazil votes"}')
    assert agent.dropped_fields == {"why": 2}
    assert agent.failures == 0


def test_a_reply_that_does_not_fit_costs_one_message(capsys):
    model = Scripted(lambda m: '{"on_topic": "maybe"}' if "Ottawa" in m["title"]
                     else '{"on_topic": "yes"}')
    register_backend("scripted_test2", lambda: model)
    agent = role_agent("Felix", english_call(TOPIC, ai="scripted_test2"), TOPIC)
    out, net = run_through(agent, [{"title": "Brazil"}, {"title": "Ottawa"}, {"title": "Lima"}])
    assert [m["title"] for m in out] == ["Brazil", "Lima"]
    assert agent.failures == 1
    assert "'on_topic' is 'maybe'" in agent.first_failure
    assert "does not fit its front matter" in capsys.readouterr().err
    net.print_run_summary()
    assert "failed on 1 message(s)" in capsys.readouterr().out


def test_the_summary_notes_dropped_fields(capsys):
    model = Scripted(lambda m: '{"on_topic": "yes", "reason": "r"}')
    register_backend("scripted_test3", lambda: model)
    agent = role_agent("Felix", english_call(TOPIC, ai="scripted_test3"), TOPIC)
    _, net = run_through(agent, [{"title": "a"}, {"title": "b"}])
    net.print_run_summary()
    # The network names the agent after its block: root::role.
    assert "root::role's replies had fields its out: does not declare; they were " \
           "dropped: reason (2)." in capsys.readouterr().out


# ── Python roles ───────────────────────────────────────────────────────────

CLERK = '''"""
---
in: amount
out: clerk_decision (approve | escalate)
---
"""
from _limits import DEFAULT_LIMIT


def step(item, settings):
    if item["amount"] < settings["limit"]:
        return {"clerk_decision": "approve"}
    return {"clerk_decision": "escalate"}


class Clerk:
    def __init__(self, limit=DEFAULT_LIMIT):
        self.settings = {"limit": limit}

    def __call__(self, item):
        return step(item, self.settings)
'''


@pytest.fixture
def roles(tmp_path: Path) -> Path:
    folder = tmp_path / "office" / "roles"
    folder.mkdir(parents=True)
    (folder / "_limits.py").write_text("DEFAULT_LIMIT = 50\n")
    (folder / "clerk.py").write_text(CLERK)
    return folder


def test_a_python_annotator_with_a_helper_module_and_arguments(roles):
    path = roles / "clerk.py"
    fm = read_front_matter(path)
    agent = role_agent("Clerk", python_call(path, fm, {"limit": 30}), fm)
    out, _ = run_through(agent, [{"amount": 20}, {"amount": 40}])
    assert [m["clerk_decision"] for m in out] == ["approve", "escalate"]


def test_a_python_author_is_a_flat_map(tmp_path):
    path = tmp_path / "splitter.py"
    path.write_text('"""\n---\nkind: author\nout: word\n---\n"""\n'
                    "class Splitter:\n"
                    "    def __call__(self, item):\n"
                    "        return [{'word': w} for w in item['text'].split()]\n")
    fm = read_front_matter(path)
    agent = role_agent("S", python_call(path, fm, {}), fm)
    assert isinstance(agent, AuthorAgent)
    out, _ = run_through(agent, [{"text": "a b c"}, {"text": ""}, {"text": "d"}])
    assert [m["word"] for m in out] == ["a", "b", "c", "d"]


def test_a_python_role_that_raises_costs_one_message(tmp_path):
    path = tmp_path / "picky.py"
    path.write_text("class Picky:\n"
                    "    def __call__(self, item):\n"
                    "        if item['n'] == 2:\n"
                    "            raise ValueError('not two')\n"
                    "        return {'ok': 'yes'}\n")
    agent = role_agent("P", python_call(path, read_front_matter(path), {}),
                       read_front_matter(path))
    out, _ = run_through(agent, [{"n": 1}, {"n": 2}, {"n": 3}])
    assert [m["n"] for m in out] == [1, 3]
    assert agent.failures == 1 and "not two" in agent.first_failure


@pytest.mark.parametrize("source, message", [
    ("x = 1\n", "exactly one class; it defines none"),
    ("class A: pass\nclass B: pass\n", "exactly one class; it defines A, B"),
    ("from collections import OrderedDict\n", "exactly one class; it defines none"),
    ("class A:\n    def __init__(self):\n        pass\n", r"A\(limit\) failed"),
])
def test_python_role_load_errors(tmp_path, source, message):
    path = tmp_path / "bad.py"
    path.write_text(source)
    with pytest.raises(RoleLoadError, match=message):
        python_call(path, read_front_matter(path), {"limit": 1})


def test_needs_is_checked_before_anything_is_imported(tmp_path):
    path = tmp_path / "birds.py"
    path.write_text('"""\n---\nneeds: json, no_such_package_xyz\n---\n"""\n'
                    "raise SystemExit('the file must not be imported')\n")
    with pytest.raises(RoleLoadError, match="needs no_such_package_xyz.*pip install "
                                            "no_such_package_xyz"):
        python_call(path, read_front_matter(path), {})
