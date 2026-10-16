"""End-to-end: offices run the way a student runs them.

Each test copies an office into a temporary folder and runs ``dsl run``
on it in a separate Python process -- the same path a student takes:
``cli.main`` -> generated ``build/run.py`` -> the runtime. Language
models are replaced by ``tests/e2e/fake_model.py``, which answers from a
script, so the runs need no network and no API key and always give the
same replies.

Why these exist (restructure_plan.md, 17 October): the rest of the suite
tests the runtime and the compiler in isolation, and no test ran an office
through ``dsl run``. Two faults lived in that gap for months: the gallery
sweep compiled offices by a path ``dsl run`` never takes, and process mode
did not work at all. The labs depend on four things, and each has a test
here:

1. an office with a finite input stops by itself, with a summary;
2. a role that fails costs one message, is reported, and makes the exit
   code non-zero;
3. a guardrail fires: a model's reply that breaks the role's declared
   interface is caught and counted, not passed on;
4. a loop that stalls is reported as stalled (not yet built: xfail).

These use today's office language. When the spec's language replaces it,
the offices here are rewritten; the four properties stay.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
GALLERY = REPO / "dissyslab" / "gallery"


def run_office(office: Path, script: list[dict] | None = None, timeout: int = 60):
    """Run ``dsl run office`` in a fresh process; return (exit code, output, log).

    ``script`` is the fake model's rules (see fake_model.py); ``log`` is
    the list of model calls it recorded.
    """
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(
        [str(REPO)] + ([env["PYTHONPATH"]] if env.get("PYTHONPATH") else [])
    )
    env.pop("DSL_BACKEND", None)
    log_path = office.parent / f"{office.name}_model_calls.jsonl"
    if script is not None:
        script_path = office.parent / f"{office.name}_script.json"
        script_path.write_text(json.dumps(script), encoding="utf-8")
        env["DSL_BACKEND_MODULE"] = "tests.e2e.fake_model"
        env["DSL_FAKE_SCRIPT"] = str(script_path)
        env["DSL_FAKE_LOG"] = str(log_path)
    proc = subprocess.run(
        [sys.executable, "-c",
         "import sys; from dissyslab.cli import main; sys.exit(main(sys.argv[1:]))",
         "run", str(office)],
        cwd=office, env=env, capture_output=True, text=True, timeout=timeout,
    )
    calls = []
    if log_path.exists():
        calls = [json.loads(line) for line in log_path.read_text().splitlines()]
    return proc.returncode, proc.stdout + proc.stderr, calls


def copy_office(src: Path, tmp_path: Path) -> Path:
    """Copy a gallery office without its build output or earlier results."""
    dst = tmp_path / src.name
    shutil.copytree(
        src, dst,
        ignore=shutil.ignore_patterns("build", "__pycache__", "*.jsonl", "trace", "snapshots"),
    )
    # Keep input data files that are .jsonl (e.g. debate's problem bank).
    for data in src.glob("problems.jsonl"):
        shutil.copy(data, dst / data.name)
    return dst


def lines_of(path: Path) -> list[dict]:
    """The JSON objects in a .jsonl file, skipping blank and # lines."""
    return [
        json.loads(x) for x in path.read_text().splitlines()
        if x.strip() and not x.lstrip().startswith("#")
    ]


# ── Scripts for the debate office ────────────────────────────────────────────

def _panel(answer: str = "A") -> list[dict]:
    reply = '{"%s": {"answer": "' + answer + '", "reasoning": "r", "confidence": 0.9}}'
    return [
        {"when": "You are an agent named **Qwen**", "reply": reply % "qwen"},
        {"when": "You are an agent named **GPT**", "reply": reply % "gpt"},
        {"when": "You are an agent named **Claude**", "reply": reply % "claude"},
    ]


FINISH = {
    "when": "You are Riley",
    "reply": json.dumps({
        "send_to": "finish", "problem_id": "$problem_id", "final_answer": "A",
        "final_reasoning": "all agree", "agreement": "unanimous",
        "rounds_used": 1, "text": "done",
    }),
}


# ── 1. A finite office stops by itself ───────────────────────────────────────


def test_python_office_stops_by_itself(tmp_path):
    """returns_desk: four tickets, a select loop, no model."""
    office = copy_office(GALLERY / "apps" / "returns_desk", tmp_path)
    code, out, _ = run_office(office)
    assert code == 0, out
    assert "Run summary" in out
    outcomes = lines_of(office / "outcomes.jsonl")
    assert [o["ticket_id"] for o in outcomes] == ["T1", "T2", "T3", "T4"]
    assert [o["decided_by"] for o in outcomes] == ["clerk", "manager", "clerk", "manager"]


def test_synchronizer_office_stops_by_itself(tmp_path):
    """room_climate_monitor: two sensors joined by a synchronizer."""
    office = copy_office(GALLERY / "apps" / "room_climate_monitor", tmp_path)
    code, out, _ = run_office(office)
    assert code == 0, out
    assert out.count("'alert': True") == 2, out


def test_llm_debate_stops_after_the_last_problem(tmp_path):
    """debate: three models and a moderator, one problem at a time."""
    office = copy_office(GALLERY / "apps" / "debate", tmp_path)
    n_problems = len(lines_of(office / "problems.jsonl"))
    code, out, calls = run_office(office, _panel() + [FINISH])
    assert code == 0, out
    answers = lines_of(office / "debate_answers.jsonl")
    assert len(answers) == n_problems
    assert len(calls) == 4 * n_problems  # three panellists and Riley, once each


def test_llm_debate_loop_takes_a_second_round(tmp_path):
    """debate: the moderator sends the first problem back for one more round."""
    office = copy_office(GALLERY / "apps" / "debate", tmp_path)
    n_problems = len(lines_of(office / "problems.jsonl"))
    first_id = lines_of(office / "problems.jsonl")[0]["id"]
    again = {
        "when": "You are Riley",
        # Round 0 of the first problem only.
        "user_contains": [f'"{first_id}"', '"history": []'],
        "reply": json.dumps({
            "send_to": "continue", "problem_id": "$problem_id", "problem": "?",
            "round": 1, "history": [{"round": 0}], "text": "again",
        }),
    }
    code, out, calls = run_office(office, _panel() + [again, FINISH])
    assert code == 0, out
    assert len(lines_of(office / "debate_answers.jsonl")) == n_problems
    assert len(calls) == 4 * n_problems + 4  # one extra round of four calls


# ── 2. A failing role costs one message ──────────────────────────────────────

FAILING_OFFICE = """\
# Office: failing

Sources: file_source(filepath="items.jsonl")
Sinks: jsonl_recorder(path="done.jsonl")

Agents:
Pat is a picky.

Connections:
file_source's destination is Pat.
Pat's out is jsonl_recorder.
"""

PICKY_ROLE = '''\
from dissyslab.blocks.role import Role
from dissyslab.office.library import AgentRoleEntry


def picky(msg):
    if msg["n"] == 2:
        raise ValueError("I do not like two")
    return [(msg, "out")]


role = AgentRoleEntry(
    name="picky", in_ports=("in_",), out_ports=("out",),
    factory=lambda: Role(fn=picky, statuses=["out"]),
)
'''


def test_a_failing_role_costs_one_message(tmp_path):
    office = tmp_path / "failing"
    (office / "roles").mkdir(parents=True)
    (office / "office.md").write_text(FAILING_OFFICE)
    (office / "roles" / "picky.py").write_text(PICKY_ROLE)
    (office / "items.jsonl").write_text("".join(json.dumps({"n": n}) + "\n" for n in (1, 2, 3)))
    code, out, _ = run_office(office)
    assert code != 0, out
    assert "I do not like two" in out
    assert [m["n"] for m in lines_of(office / "done.jsonl")] == [1, 3]


# ── 3. A guardrail fires ─────────────────────────────────────────────────────

FILTER_OFFICE = """\
# Office: guarded

Sources: file_source(filepath="articles.jsonl")
Sinks: jsonl_recorder(path="kept.jsonl"), jsonl_recorder_discard(path="dropped.jsonl")

Agents:
Felix is a filter.

Connections:
file_source's destination is Felix.
Felix's keeper is jsonl_recorder.
Felix's discard is jsonl_recorder_discard.
"""

FILTER_ROLE = textwrap.dedent("""\
    ---
    outboxes: keeper, discard
    adds: text
    ---
    You are a content filter. Decide if each article is about the
    Americas. If it is, send to keeper. Otherwise send to discard.
""")


def test_a_reply_outside_the_declared_interface_is_caught(tmp_path):
    """The model names an outbox the role does not have: counted, not passed on."""
    office = tmp_path / "guarded"
    (office / "roles").mkdir(parents=True)
    (office / "office.md").write_text(FILTER_OFFICE)
    (office / "roles" / "filter.md").write_text(FILTER_ROLE)
    titles = ["Brazil votes", "Tokyo rains", "Ottawa budget"]
    (office / "articles.jsonl").write_text(
        "".join(json.dumps({"title": t, "text": t}) + "\n" for t in titles))
    script = [
        {"when": "content filter", "user_contains": "Brazil",
         "reply": '{"send_to": "keeper", "text": "Brazil votes"}'},
        {"when": "content filter", "user_contains": "Tokyo",
         "reply": '{"send_to": "discard", "text": "Tokyo rains"}'},
        {"when": "content filter", "user_contains": "Ottawa",
         "reply": '{"send_to": "maybe", "text": "Ottawa budget"}'},
    ]
    code, out, calls = run_office(office, script)
    assert len(calls) == 3
    assert code != 0, out
    assert "maybe" in out
    assert [a["title"] for a in lines_of(office / "kept.jsonl")] == ["Brazil votes"]
    assert [a["title"] for a in lines_of(office / "dropped.jsonl")] == ["Tokyo rains"]


# ── 4. A stalled loop is reported ────────────────────────────────────────────


@pytest.mark.xfail(strict=True, reason="stall report not built yet (spec section 4.5, item 6)")
def test_a_stalled_loop_is_reported(tmp_path):
    """The moderator fails on one problem, so the gate never releases the rest.

    Today the office stops, exits non-zero and reports Riley's failure, but
    does not say that the remaining problems were never attempted.
    """
    office = copy_office(GALLERY / "apps" / "debate", tmp_path)
    second_id = lines_of(office / "problems.jsonl")[1]["id"]
    bad = {"when": "You are Riley", "user_contains": second_id,
           "reply": '{"send_to": "maybe", "text": "?"}'}
    code, out, _ = run_office(office, _panel() + [bad, FINISH])
    assert code != 0, out
    # The report's exact wording is decided when it is built; it will
    # start with "Stalled:". (Not "stalled" in any case: pytest's
    # temporary folder for this test is named after it.)
    assert "Stalled:" in out
