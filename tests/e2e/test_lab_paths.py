"""End-to-end: offices run the way a student runs them.

Each test copies an office into a temporary folder and runs ``dsl run``
on it in a separate Python process -- the same path a student takes:
``cli.main`` -> ``office.build`` -> the runtime. Language
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
4. a loop that stalls is reported as stalled (test_dsl_new_path.py).

Rewritten for the 2.0 office language and gallery in Phase 6a; the four
properties are the ones the version 1 tests checked.
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
        calls = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()]
    return proc.returncode, proc.stdout + proc.stderr, calls


def copy_office(name: str, tmp_path: Path) -> Path:
    """Copy a gallery office into a temporary folder (a run writes beside it)."""
    dst = tmp_path / name
    shutil.copytree(GALLERY / name, dst, ignore=shutil.ignore_patterns("__pycache__"))
    return dst


def lines_of(path: Path) -> list[dict]:
    """The JSON objects in a .jsonl file, skipping blank and # lines."""
    return [
        json.loads(x) for x in path.read_text(encoding="utf-8").splitlines()
        if x.strip() and not x.lstrip().startswith("#")
    ]


def write_office(folder: Path, files: dict[str, str]) -> Path:
    for rel, text in files.items():
        (folder / rel).parent.mkdir(parents=True, exist_ok=True)
        (folder / rel).write_text(text, encoding="utf-8")
    return folder


# ── Scripts for the debate office ────────────────────────────────────────────

def _panel(answer: str = "A") -> list[dict]:
    return [{"when": f"You are {who},",
             "reply": json.dumps({key: {"answer": answer, "reasoning": "r",
                                        "confidence": 0.9}})}
            for who, key in (("Qwen", "qwen"), ("GPT", "gpt"), ("Claude", "claude"))]


AGREE = {"when": "You moderate a panel",
         "reply": json.dumps({"agreement": "unanimous", "final_answer": "A", "note": ""})}


# ── 1. A finite office stops by itself ───────────────────────────────────────


def test_python_office_stops_by_itself(tmp_path):
    """returns_desk: four tickets, a gate, no model."""
    office = copy_office("returns_desk", tmp_path)
    code, out, _ = run_office(office)
    assert code == 0, out
    assert "Run summary" in out
    # Not in ticket order: a decision reaches the log and releases the next
    # ticket in parallel. Compare by ticket.
    outcomes = sorted(lines_of(office / "outcomes.jsonl"), key=lambda o: o["ticket_id"])
    assert [o["ticket_id"] for o in outcomes] == ["T1", "T2", "T3", "T4"]
    assert [o.get("manager_decision") for o in outcomes] == [None, "approve", None, "approve"]


def test_synchronizer_office_stops_by_itself(tmp_path):
    """room_climate_monitor: two sensors joined by a synchronizer."""
    office = copy_office("room_climate_monitor", tmp_path)
    code, out, _ = run_office(office)
    assert code == 0, out
    assert out.count("'alert': 'yes'") == 2, out


def test_llm_debate_stops_after_the_last_problem(tmp_path):
    """debate: three models and a moderator, one problem at a time."""
    office = copy_office("debate", tmp_path)
    n_problems = len(lines_of(office / "problems.jsonl"))
    code, out, calls = run_office(office, _panel() + [AGREE])
    assert code == 0, out
    assert len(lines_of(office / "debate_answers.jsonl")) == n_problems
    assert len(calls) == 4 * n_problems  # three panellists and Riley, once each


def test_llm_debate_loop_takes_a_second_round(tmp_path):
    """debate: the moderator finds no agreement on round 0 of the first problem."""
    office = copy_office("debate", tmp_path)
    problems = lines_of(office / "problems.jsonl")
    first_id = problems[0]["problem_id"]
    split = {"when": "You moderate a panel",
             "user_contains": [f'"{first_id}"', '"round": 0'],
             "reply": json.dumps({"agreement": "none", "final_answer": "A",
                                  "note": "check again"})}
    code, out, calls = run_office(office, _panel() + [split, AGREE])
    assert code == 0, out
    answers = {a["problem_id"]: a for a in lines_of(office / "debate_answers.jsonl")}
    assert len(answers) == len(problems)
    assert answers[first_id]["rounds_used"] == 2
    assert len(calls) == 4 * len(problems) + 4  # one extra round of four calls


# ── 2. A failing role costs one message ──────────────────────────────────────

FAILING = {
    "office.md": (
        "sources:\n    items: file_source(path=\"items.jsonl\")\n"
        "sinks:\n    jsonl_recorder(path=\"done.jsonl\")\n"
        "agents:\n    Pat: picky\n"
        "connections:\n    items -> Pat -> jsonl_recorder\n"),
    "roles/picky.py": (
        '"""\n---\nin: n\n---\n"""\n\n\n'
        "class Picky:\n"
        "    def __call__(self, item):\n"
        "        if item[\"n\"] == 2:\n"
        "            raise ValueError(\"I do not like two\")\n"
        "        return {}\n"),
    "items.jsonl": "".join(json.dumps({"n": n}) + "\n" for n in (1, 2, 3)),
}


def test_a_failing_role_costs_one_message(tmp_path):
    office = write_office(tmp_path / "failing", FAILING)
    code, out, _ = run_office(office)
    assert code != 0, out
    assert "I do not like two" in out
    assert sorted(m["n"] for m in lines_of(office / "done.jsonl")) == [1, 3]


# ── 3. A guardrail fires ─────────────────────────────────────────────────────

GUARDED = {
    "office.md": (
        "sources:\n    articles: file_source(path=\"articles.jsonl\")\n"
        "sinks:\n    kept: jsonl_recorder(path=\"kept.jsonl\")\n"
        "    dropped: jsonl_recorder(path=\"dropped.jsonl\")\n"
        "agents:\n    Felix: americas\n    Rex: router(on=\"on_topic\")\n"
        "connections:\n    articles -> Felix -> Rex\n"
        "    Rex.yes -> kept\n    Rex.no -> dropped\n"),
    "roles/americas.md": textwrap.dedent("""\
        ---
        in: title
        out: on_topic (yes | no)
        ---
        You are a content filter. Decide whether the article is about the
        Americas.
        """),
    "articles.jsonl": "".join(json.dumps({"title": t}) + "\n"
                              for t in ("Brazil votes", "Tokyo rains", "Ottawa budget")),
}


def test_a_reply_outside_the_declared_interface_is_caught(tmp_path):
    """The model answers a value the role does not declare: counted, not passed on."""
    office = write_office(tmp_path / "guarded", GUARDED)
    script = [
        {"when": "content filter", "user_contains": "Brazil", "reply": '{"on_topic": "yes"}'},
        {"when": "content filter", "user_contains": "Tokyo", "reply": '{"on_topic": "no"}'},
        {"when": "content filter", "user_contains": "Ottawa", "reply": '{"on_topic": "maybe"}'},
    ]
    code, out, calls = run_office(office, script)
    assert len(calls) == 3
    assert code != 0, out
    assert "maybe" in out
    assert [a["title"] for a in lines_of(office / "kept.jsonl")] == ["Brazil votes"]
    assert [a["title"] for a in lines_of(office / "dropped.jsonl")] == ["Tokyo rains"]


# 4. A stalled loop is reported: tests/e2e/test_dsl_new_path.py
#    (test_a_stalled_loop_is_reported), on the debate office.
