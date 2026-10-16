"""Offices in the new line syntax, built and run end to end (Phase 3.3).

Each test writes an office folder -- office.md in the line form, its
roles, its data -- and runs it with ``run_office``. English roles use a
scripted model registered for the test.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from dissyslab.backends import register_backend
from dissyslab.office.build import BuildError, build_office, run_office


def write(folder: Path, files: dict[str, str]) -> Path:
    for rel, text in files.items():
        path = folder / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    return folder


def jsonl(items: list[dict]) -> str:
    return "".join(json.dumps(i) + "\n" for i in items)


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(x) for x in path.read_text().splitlines() if x.strip()]


class Scripted:
    def __init__(self, answer):
        self.answer = answer

    def complete(self, *, system, user, max_tokens=1024, temperature=1.0, model=None):
        return self.answer(system, json.loads(user))


TOPIC_FILTER = """\
---
emits: whether a news article is on the topic
in: title, text
out: on_topic (yes | no)
---
You read one news article. Decide whether it is about the Americas.
Return only a JSON object with one field, "on_topic", "yes" or "no".
"""

WORD_COUNT = '''"""
---
emits: how many words the article has
in: text
out: words
---
"""


class WordCount:
    def __call__(self, item):
        return {"words": len(item["text"].split())}
'''

ARTICLES = [
    {"title": "Brazil votes", "text": "Brazil votes today"},
    {"title": "Tokyo rains", "text": "Rain in Tokyo"},
    {"title": "Ottawa budget", "text": "The Ottawa budget passes"},
]


@pytest.fixture
def americas_model():
    register_backend("americas_test", lambda: Scripted(
        lambda system, m: json.dumps(
            {"on_topic": "no" if "Tokyo" in m["title"] else "yes"})))


def test_a_pipeline_of_an_english_and_a_python_role(tmp_path, americas_model):
    office = write(tmp_path / "pipeline", {
        "office.md": (
            "# a pipeline: an English role, then a Python role\n"
            "sources:\n"
            "    articles: file_source(path=\"articles.jsonl\")\n"
            "sinks:\n"
            "    jsonl_recorder(path=\"out.jsonl\")\n"
            "agents:\n"
            "    Felix: topic_filter(ai=\"americas_test\")\n"
            "    Wendy: word_count\n"
            "connections:\n"
            "    articles -> Felix -> Wendy -> jsonl_recorder\n"),
        "roles/topic_filter.md": TOPIC_FILTER,
        "roles/word_count.py": WORD_COUNT,
        "articles.jsonl": jsonl(ARTICLES),
    })
    assert run_office(office) == 0
    out = read_jsonl(office / "out.jsonl")
    assert [(m["title"], m["on_topic"], m["words"]) for m in out] == [
        ("Brazil votes", "yes", 3), ("Tokyo rains", "no", 3), ("Ottawa budget", "yes", 4)]


def test_fan_in_and_fan_out_with_named_sinks(tmp_path, americas_model):
    office = write(tmp_path / "fan", {
        "office.md": (
            "sources:\n"
            "    first: file_source(path=\"a.jsonl\")\n"
            "    second: file_source(path=\"b.jsonl\")\n"
            "sinks:\n"
            "    left: jsonl_recorder(path=\"left.jsonl\")\n"
            "    right: jsonl_recorder(path=\"right.jsonl\")\n"
            "agents:\n"
            "    Felix: topic_filter(ai=\"americas_test\")\n"
            "connections:\n"
            "    first, second -> Felix -> left, right\n"),
        "roles/topic_filter.md": TOPIC_FILTER,
        "a.jsonl": jsonl(ARTICLES[:2]),
        "b.jsonl": jsonl(ARTICLES[2:]),
    })
    assert run_office(office) == 0
    for sink in ("left.jsonl", "right.jsonl"):
        assert sorted(m["title"] for m in read_jsonl(office / sink)) == sorted(
            a["title"] for a in ARTICLES)


def test_a_local_source_and_sink(tmp_path):
    office = write(tmp_path / "local", {
        "office.md": (
            "sources:\n    numbers: counter(upto=3)\n"
            "sinks:\n    keep: keeper(path=\"kept.txt\")\n"
            "connections:\n    numbers -> keep\n"),
        "sources/counter.py": (
            "class Counter:\n"
            "    def __init__(self, upto):\n"
            "        self.n, self.upto = 0, upto\n"
            "    def __call__(self):\n"
            "        self.n += 1\n"
            "        return {'n': self.n} if self.n <= self.upto else None\n"),
        "sinks/keeper.py": (
            "class Keeper:\n"
            "    def __init__(self, path):\n"
            "        self.path = path\n"
            "    def __call__(self, msg):\n"
            "        with open(self.path, 'a') as f:\n"
            "            f.write(str(msg['n']) + '\\n')\n"),
    })
    assert run_office(office) == 0
    assert (office / "kept.txt").read_text().split() == ["1", "2", "3"]


def test_a_failing_message_makes_the_exit_code_non_zero(tmp_path):
    register_backend("half_test", lambda: Scripted(
        lambda system, m: '{"on_topic": "maybe"}' if "Tokyo" in m["title"]
        else '{"on_topic": "yes"}'))
    office = write(tmp_path / "half", {
        "office.md": (
            "sources:\n    articles: file_source(path=\"articles.jsonl\")\n"
            "sinks:\n    jsonl_recorder(path=\"out.jsonl\")\n"
            "agents:\n    Felix: topic_filter(ai=\"half_test\")\n"
            "connections:\n    articles -> Felix -> jsonl_recorder\n"),
        "roles/topic_filter.md": TOPIC_FILTER,
        "articles.jsonl": jsonl(ARTICLES),
    })
    assert run_office(office) == 1
    assert len(read_jsonl(office / "out.jsonl")) == 2


# ── Clear errors for what is not built yet, or not right ───────────────────


@pytest.mark.parametrize("agents, connections, message", [
    ("    Rex: router(on=\"on_topic\")\n", "    articles -> Rex\n", "Rex sends nowhere"),
    ("    Rex: router\n    Felix: topic_filter\n", "    articles -> Rex\n    Rex.yes -> Felix\n",
     "every router names its field"),
    ("    Rex: router(on=\"x\")\n    Felix: topic_filter\n",
     "    articles -> Rex -> Felix\n", "outboxes are named by values"),
    ("    G: gate(size=2)\n", "    articles -> G\n", "a gate takes no arguments"),
    ("    G: gate\n", "    articles -> G.ready\n", "G has inboxes in and done; it has no 'ready'"),
    ("    S: synchronizer\n", "    articles -> S.a\n", "every synchronizer names its key"),
    ("    S: synchronizer(on=\"url\")\n", "    articles -> S\n", "inboxes are named by its connections"),
    ("    S: synchronizer(on=\"url\")\n", "    articles -> S.a\n", "needs at least two inboxes"),
    ("    Jay: unassigned\n", "    articles -> Jay\n", "Jay is unassigned"),
    ("    Felix: topic_filter(focus=\"x\")\n", "    articles -> Felix\n",
     "an English role takes only ai=, not focus"),
    ("    Felix: topic_filter\n", "    articles -> Felix.left\n", "Felix has inbox in; it has no 'left'"),
    ("    Felix: topic_fliter\n", "    articles -> Felix\n",
     "line 4: no agent called 'topic_fliter'.*Did you mean 'topic_filter'"),
])
def test_build_errors(tmp_path, agents, connections, message):
    office = write(tmp_path / "bad", {
        "office.md": ("sources:\n    articles: file_source(path=\"a.jsonl\")\n"
                      f"agents:\n{agents}connections:\n{connections}"),
        "roles/topic_filter.md": TOPIC_FILTER,
        "a.jsonl": jsonl(ARTICLES),
    })
    with pytest.raises(BuildError, match=message):
        build_office(office)


# ── Routers (spec section 5) ───────────────────────────────────────────────


def _news_filter(tmp_path: Path, routes: str, model: str) -> Path:
    return write(tmp_path / "news_filter", {
        "office.md": (
            "# org_news_filter, as ported (officespeak_ports/org_news_filter.md)\n"
            "sources:\n    articles: file_source(path=\"articles.jsonl\")\n"
            "sinks:\n"
            "    kept: jsonl_recorder(path=\"kept.jsonl\")\n"
            "    other: jsonl_recorder(path=\"other.jsonl\")\n"
            "    discard\n"
            f"agents:\n    Felix: topic_filter(ai=\"{model}\")\n"
            "    Rex: router(on=\"on_topic\")\n"
            "connections:\n    articles -> Felix -> Rex\n" + routes),
        "roles/topic_filter.md": TOPIC_FILTER,
        "articles.jsonl": jsonl(ARTICLES),
    })


def test_a_router_sends_by_value(tmp_path, americas_model):
    office = _news_filter(tmp_path, "    Rex.yes -> kept\n    Rex.no -> discard\n",
                          "americas_test")
    assert run_office(office) == 0
    kept = read_jsonl(office / "kept.jsonl")
    assert [m["title"] for m in kept] == ["Brazil votes", "Ottawa budget"]
    assert all(m["on_topic"] == "yes" for m in kept)  # the field stays


def test_otherwise_takes_the_values_with_no_outbox(tmp_path):
    register_backend("three_way_test", lambda: Scripted(
        lambda system, m: json.dumps({"on_topic": {"Brazil votes": "yes", "Tokyo rains": "no"}
                                      .get(m["title"], "unsure")})))
    office = _news_filter(tmp_path, "    Rex.yes -> kept\n    Rex.otherwise -> other\n",
                          "three_way_test")
    # "unsure" is not in out: (yes | no), so the role's reply is rejected
    # before it reaches Rex; "no" has no outbox and goes to otherwise.
    assert run_office(office) == 1
    assert [m["title"] for m in read_jsonl(office / "kept.jsonl")] == ["Brazil votes"]
    assert [m["title"] for m in read_jsonl(office / "other.jsonl")] == ["Tokyo rains"]


def test_a_value_with_no_outbox_and_no_otherwise_is_a_failure(tmp_path, americas_model, capsys):
    office = _news_filter(tmp_path, "    Rex.yes -> kept\n", "americas_test")
    assert run_office(office) == 1
    assert [m["title"] for m in read_jsonl(office / "kept.jsonl")] == [
        "Brazil votes", "Ottawa budget"]
    err = capsys.readouterr().err
    assert "'on_topic' is 'no', which has no outbox here and there is no otherwise" in err


# ── The gate (spec section 6): returns_desk, as ported ─────────────────────

CLERK_ROLE = '''"""
---
emits: approves small refunds; escalates the rest
in: amount
out: clerk_decision (approve | escalate)
---
"""


def step(item, settings):
    if item["amount"] < settings["limit"]:
        return {"clerk_decision": "approve"}
    return {"clerk_decision": "escalate"}


class Clerk:
    def __init__(self, limit=50):
        self.settings = {"limit": limit}

    def __call__(self, item):
        return step(item, self.settings)
'''

MANAGER_ROLE = '''"""
---
emits: the manager's decision on an escalated refund
in: amount
out: manager_decision (approve | refuse)
---
"""


class Manager:
    def __call__(self, item):
        return {"manager_decision": "approve"}
'''

TICKETS = [
    {"ticket_id": "T1", "customer": "Ana", "amount": 20},
    {"ticket_id": "T2", "customer": "Ben", "amount": 120},
    {"ticket_id": "T3", "customer": "Cy", "amount": 35},
    {"ticket_id": "T4", "customer": "Dee", "amount": 80},
]


def test_returns_desk_one_ticket_at_a_time(tmp_path):
    office = write(tmp_path / "returns_desk", {
        "office.md": (
            "sources:\n    tickets: file_source(path=\"tickets.jsonl\")\n"
            "sinks:\n    jsonl_recorder(path=\"outcomes.jsonl\")\n"
            "agents:\n"
            "    Gate: gate\n"
            "    Clerk: clerk(limit=50)\n"
            "    Rex: router(on=\"clerk_decision\")\n"
            "    Manager: manager\n"
            "connections:\n"
            "    tickets -> Gate -> Clerk -> Rex\n"
            "    Rex.approve -> jsonl_recorder, Gate.done\n"
            "    Rex.escalate -> Manager -> jsonl_recorder, Gate.done\n"),
        "roles/clerk.py": CLERK_ROLE,
        "roles/manager.py": MANAGER_ROLE,
        "tickets.jsonl": jsonl(TICKETS),
    })
    assert run_office(office) == 0
    # The gate admits one ticket at a time, but a decision goes to the
    # recorder and to Gate.done in parallel, so the next ticket can reach
    # the recorder first: the log is not in ticket order. Compare by ticket.
    outcomes = sorted(read_jsonl(office / "outcomes.jsonl"), key=lambda o: o["ticket_id"])
    assert [o["ticket_id"] for o in outcomes] == ["T1", "T2", "T3", "T4"]
    assert [(o["clerk_decision"], o.get("manager_decision")) for o in outcomes] == [
        ("approve", None), ("escalate", "approve"), ("approve", None), ("escalate", "approve")]


# ── The keyed synchronizer (spec section 6) ────────────────────────────────

ENTITIES = '''"""
---
in: text
out: entities
---
"""


class Entities:
    def __call__(self, item):
        return {"entities": [w for w in item["text"].split() if w[:1].isupper()]}
'''

SEVERITY = '''"""
---
in: text
out: severity (HIGH | LOW)
---
"""


class Severity:
    def __call__(self, item):
        if "fail" in item["text"]:
            return {"severity": "SEVERE"}      # not in out: -- rejected
        return {"severity": "HIGH" if "war" in item["text"] else "LOW"}
'''

STORIES = [
    {"url": "u1", "text": "Peace talks in Geneva"},
    {"url": "u2", "text": "this one will fail"},
    {"url": "u3", "text": "war in Europe"},
]


def _fan_out_office(tmp_path: Path, sync_line: str, *, topic_twice: bool = False) -> Path:
    return write(tmp_path / "situation", {
        "office.md": (
            "sources:\n    stories: file_source(path=\"stories.jsonl\")\n"
            "sinks:\n    jsonl_recorder(path=\"out.jsonl\")\n"
            "agents:\n    Eve: entities\n    Sam: severity\n"
            f"    Sync: {sync_line}\n"
            "connections:\n"
            "    stories -> Eve, Sam\n"
            "    Eve -> Sync.entities\n"
            "    Sam -> Sync.severity\n"
            "    Sync -> jsonl_recorder\n"),
        "roles/entities.py": ENTITIES,
        "roles/severity.py": SEVERITY,
        "stories.jsonl": jsonl(STORIES),
    })


def test_a_dropped_message_costs_only_its_own_group(tmp_path, capsys):
    office = _fan_out_office(tmp_path, 'synchronizer(on="url")')
    assert run_office(office) == 1
    out = {m["url"]: m for m in read_jsonl(office / "out.jsonl")}
    # u1 and u3 are complete and correctly merged; u2 lost only itself.
    assert sorted(out) == ["u1", "u3"]
    assert out["u1"] == {"url": "u1", "text": "Peace talks in Geneva",
                         "entities": ["Peace", "Geneva"], "severity": "LOW"}
    assert out["u3"]["severity"] == "HIGH" and out["u3"]["entities"] == ["Europe"]
    err = capsys.readouterr().err
    assert "group url=u2 is missing severity" in err
    # The walk back from the inbox the group lacks ends at the finished source.
    assert ("Stalled: situation::Sync holds an incomplete group: url=u2 "
            "(has entities; missing severity)") in err
    assert "situation::Sync.severity <- situation::Sam.out: empty; " \
           "situation::Sam is idle, waiting on in" in err
    assert "situation::stories has finished" in err


def test_the_collected_form(tmp_path):
    office = _fan_out_office(tmp_path, 'synchronizer(on="url", collect="results")')
    assert run_office(office) == 1  # u2 still fails at Sam
    out = {m["url"]: m for m in read_jsonl(office / "out.jsonl")}
    assert set(out["u1"]) == {"url", "results"}
    assert set(out["u1"]["results"]) == {"entities", "severity"}
    assert out["u1"]["results"]["severity"]["severity"] == "LOW"


def test_a_conflict_is_reported_never_resolved(tmp_path, capsys):
    office = _fan_out_office(tmp_path, 'synchronizer(on="url")')
    # Both branches add "entities", with different values.
    (office / "roles" / "severity.py").write_text(SEVERITY.replace(
        'out: severity (HIGH | LOW)', 'out: severity (HIGH | LOW), entities').replace(
        'return {"severity": "HIGH" if "war" in item["text"] else "LOW"}',
        'return {"severity": "LOW", "entities": []}'))
    assert run_office(office) == 1
    assert not (office / "out.jsonl").read_text().strip()
    assert "'entities' differs between entities and severity" in capsys.readouterr().err


# ── Nested offices (spec section 3.4): org_two_office_news, as ported ──────

SUMMARIZE = '''"""
---
in: text
out: summary
---
"""


class Summarize:
    def __call__(self, item):
        return {"summary": item["text"].split()[0] + "..."}
'''


def _two_office_news(tmp_path: Path) -> Path:
    return write(tmp_path / "two_office_news", {
        "office.md": (
            "sources:\n    articles: file_source(path=\"articles.jsonl\")\n"
            "sinks:\n    jsonl_recorder(path=\"briefings.jsonl\")\n"
            "agents:\n"
            "    monitor: office(path=\"news_monitor\")\n"
            "    editor: office(path=\"news_editor\")\n"
            "connections:\n"
            "    articles -> monitor.articles\n"
            "    monitor.kept -> editor.articles\n"
            "    editor.briefings -> jsonl_recorder\n"),
        "articles.jsonl": jsonl(ARTICLES),
        "news_monitor/office.md": (
            "inputs:\n    articles\noutputs:\n    kept\n"
            "sinks:\n    discard\n"
            "agents:\n    Felix: topic_filter(ai=\"americas_test\")\n"
            "    Rex: router(on=\"on_topic\")\n"
            "connections:\n    articles -> Felix -> Rex\n"
            "    Rex.yes -> kept\n    Rex.no -> discard\n"),
        "news_monitor/roles/topic_filter.md": TOPIC_FILTER,
        "news_editor/office.md": (
            "inputs:\n    articles\noutputs:\n    briefings\n"
            "agents:\n    Sue: summarize\n"
            "connections:\n    articles -> Sue -> briefings\n"),
        "news_editor/roles/summarize.py": SUMMARIZE,
    })


def test_an_office_can_be_an_agent_of_a_bigger_office(tmp_path, americas_model):
    office = _two_office_news(tmp_path)
    assert run_office(office) == 0
    out = read_jsonl(office / "briefings.jsonl")
    assert [(m["title"], m["summary"]) for m in out] == [
        ("Brazil votes", "Brazil..."), ("Ottawa budget", "The...")]


def test_a_nested_office_cannot_be_run_on_its_own(tmp_path):
    office = _two_office_news(tmp_path)
    with pytest.raises(BuildError, match="meant to sit inside another office"):
        build_office(office / "news_monitor")


@pytest.mark.parametrize("old, new, message", [
    ("articles -> monitor.articles", "articles -> monitor",
     "office monitor's inputs are articles; write articles -> monitor.<input>"),
    ("monitor.kept -> editor.articles", "monitor.kpt -> editor.articles",
     "office monitor's outputs are kept"),
    ("monitor: office(path=\"news_monitor\")", "monitor: office(path=\"nowhere\")",
     "there is no office.md in"),
])
def test_nested_office_errors(tmp_path, americas_model, old, new, message):
    office = _two_office_news(tmp_path)
    md = office / "office.md"
    md.write_text(md.read_text().replace(old, new))
    with pytest.raises(BuildError, match=message):
        build_office(office)


# ── Multi-threaded agents must not be declared finished mid-message ────────
#
# A synchronizer (and the framework's fan-in agent) has one thread per
# inbox. While one thread holds a message it has received but not yet
# sent, another can answer the termination detector; answering "idle"
# then ends the run with the message lost. CI hit this on two of seven
# jobs (16 Oct 2026). These tests widen the window so it always shows.


def test_the_synchronizer_is_not_finished_while_a_group_is_in_hand(tmp_path, monkeypatch):
    import time

    from dissyslab.agents.synchronizer import SynchronizerAgent

    arrive = SynchronizerAgent._arrive

    def slow_arrive(self, inbox, msg):
        time.sleep(0.2)
        arrive(self, inbox, msg)

    monkeypatch.setattr(SynchronizerAgent, "_arrive", slow_arrive)
    office = _fan_out_office(tmp_path, 'synchronizer(on="url")')
    assert run_office(office) == 1  # u2 fails at Sam, as before
    assert sorted(m["url"] for m in read_jsonl(office / "out.jsonl")) == ["u1", "u3"]


def test_fan_in_is_not_finished_while_a_message_is_in_hand(monkeypatch):
    import time

    from dissyslab.blocks import Sink, Source
    from dissyslab.network import Network
    from dissyslab.runtime.plumbing import MergeAsynch

    send = MergeAsynch.send

    def slow_send(self, msg, port):
        time.sleep(0.2)
        send(self, msg, port)

    monkeypatch.setattr(MergeAsynch, "send", slow_send)
    a, b = iter([1, 2]), iter([3])
    out: list = []
    net = Network(blocks={"a": Source(fn=lambda: next(a, None), name="a"),
                          "b": Source(fn=lambda: next(b, None), name="b"),
                          "s": Sink(fn=out.append, name="s")},
                  connections=[("a", "out_", "s", "in_"), ("b", "out_", "s", "in_")])
    net.run_network()
    assert sorted(out) == [1, 2, 3]


# ── Stalls (spec 4.5, item 6) ──────────────────────────────────────────────

TICKER = '''"""
---
out: tick
---
A source that never finishes: one tick every 50 ms.
"""
import time


class Ticker:
    def __init__(self):
        self.n = 0

    def __call__(self):
        time.sleep(0.05)
        self.n += 1
        return {"tick": self.n}
'''

SWALLOWER = '''"""
---
kind: author
in: id
out: id
---
Sends nothing, ever: so the gate is never released.
"""


class Swallower:
    def __call__(self, item):
        return []
'''


def test_a_stall_is_found_while_the_rest_of_the_office_runs(tmp_path, capfd):
    """The ticker never finishes, so the office never terminates; the stall
    on the gate is still found and reported while it runs."""
    office = write(tmp_path / "stuck", {
        "office.md": (
            "sources:\n"
            "    items: file_source(path=\"items.jsonl\")\n"
            "    ticks: ticker\n"
            "sinks:\n"
            "    log: jsonl_recorder(path=\"ticks.jsonl\")\n"
            "agents:\n"
            "    Gate: gate\n"
            "    W: swallower\n"
            "connections:\n"
            "    items -> Gate -> W -> Gate.done\n"
            "    ticks -> log\n"),
        "sources/ticker.py": TICKER,
        "roles/swallower.py": SWALLOWER,
        "items.jsonl": jsonl([{"id": 1}, {"id": 2}]),
    })
    net = build_office(office)
    with pytest.raises(TimeoutError):
        net.run_network(timeout=3)
    err = capfd.readouterr().err
    assert "Stalled: stuck::Gate holds an item it admitted" in err, err
    assert "stuck::Gate.done <- stuck::W.out: empty; stuck::W is idle, waiting on in" in err
    assert "stuck::W.in <- stuck::Gate.out: empty; stuck::Gate is already on this path" in err
    assert "1 message(s) wait unread on stuck::Gate.in." in err
    assert err.count("Stalled:") == 1  # reported once, not every round
    assert len((office / "ticks.jsonl").read_text().splitlines()) > 5  # the rest ran on


def test_a_busy_gate_is_not_a_stall(tmp_path, capfd):
    """A gate waiting on done while the work is still going is not stalled."""
    office = write(tmp_path / "slow", {
        "office.md": (
            "sources:\n    items: file_source(path=\"items.jsonl\")\n"
            "sinks:\n    jsonl_recorder(path=\"out.jsonl\")\n"
            "agents:\n    Gate: gate\n    W: slow\n"
            "connections:\n    items -> Gate -> W -> jsonl_recorder, Gate.done\n"),
        "roles/slow.py": (
            '"""\n---\nin: id\nout: done\n---\n"""\nimport time\n\n\n'
            "class Slow:\n    def __call__(self, item):\n"
            "        time.sleep(0.4)\n        return {\"done\": \"yes\"}\n"),
        "items.jsonl": jsonl([{"id": i} for i in range(3)]),
    })
    assert run_office(office) == 0
    assert "Stalled:" not in capfd.readouterr().err


def test_a_bad_argument_to_a_built_in_component_names_the_good_ones(tmp_path):
    office = write(tmp_path / "typo", {
        "office.md": (
            "sources:\n    items: file_source(path=\"items.jsonl\")\n"
            "sinks:\n    jsonl_recorder(pth=\"out.jsonl\")\n"
            "connections:\n    items -> jsonl_recorder\n"),
        "items.jsonl": jsonl([{"n": 1}]),
    })
    with pytest.raises(BuildError) as err:
        build_office(office)
    message = str(err.value)
    assert message.startswith("line 4: sink 'jsonl_recorder' takes no argument 'pth'.")
    assert "Did you mean 'path'?" in message
