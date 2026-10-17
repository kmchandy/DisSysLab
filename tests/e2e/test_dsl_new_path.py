"""``dsl run``, ``dsl check`` and ``dsl build`` on offices in the new syntax.

Each test runs the command in a separate Python process, the way a
student runs it from a terminal. Until the old path is removed (Phase
6b), the command takes an office down the new path or the old one by the
form of its ``office.md`` (``syntax.is_old_form``); the last test pins
that choice for every office in the gallery.

Language models are replaced by ``tests/e2e/fake_model.py``.
"""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from dissyslab.office.syntax import is_old_form

REPO = Path(__file__).resolve().parents[2]
EXAMPLES = REPO / "dissyslab" / "gallery"


def dsl(*args: str, cwd: Path, script: list[dict] | None = None) -> tuple[int, str]:
    """Run ``dsl <args>`` in a fresh process; return (exit code, stdout + stderr)."""
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(
        [str(REPO)] + ([env["PYTHONPATH"]] if env.get("PYTHONPATH") else [])
    )
    env["PYTHONIOENCODING"] = "utf-8"
    env.pop("DSL_BACKEND", None)
    if script is not None:
        script_path = cwd.parent / f"{cwd.name}_script.json"
        script_path.write_text(json.dumps(script), encoding="utf-8")
        env["DSL_BACKEND_MODULE"] = "tests.e2e.fake_model"
        env["DSL_FAKE_SCRIPT"] = str(script_path)
    proc = subprocess.run(
        [sys.executable, "-c",
         "import sys; from dissyslab.cli import main; sys.exit(main(sys.argv[1:]))", *args],
        cwd=cwd, env=env, capture_output=True, text=True, encoding="utf-8", timeout=120,
    )
    return proc.returncode, proc.stdout + proc.stderr


def copy_example(name: str, tmp_path: Path) -> Path:
    dst = tmp_path / name
    shutil.copytree(EXAMPLES / name, dst, ignore=shutil.ignore_patterns("__pycache__"))
    return dst


# ── dsl run ────────────────────────────────────────────────────────────────


def test_run_stops_by_itself(tmp_path):
    office = copy_example("room_climate_monitor", tmp_path)
    code, out = dsl("run", ".", cwd=office)
    assert code == 0, out
    assert "Run summary" in out
    assert "'alert': 'yes'" in out


def test_run_with_models(tmp_path):
    """debate: three scripted panellists agree; every problem is answered."""
    office = copy_example("debate", tmp_path)
    panel = [{"when": f"You are {who},",
              "reply": json.dumps({key: {"answer": "A", "reasoning": "r", "confidence": 0.9}})}
             for who, key in (("Qwen", "qwen"), ("GPT", "gpt"), ("Claude", "claude"))]
    moderator = {"when": "You moderate a panel",
                 "reply": json.dumps({"agreement": "unanimous", "final_answer": "A",
                                      "note": ""})}
    code, out = dsl("run", ".", cwd=office, script=panel + [moderator])
    assert code == 0, out
    answers = (office / "debate_answers.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(answers) == 3


def test_run_quiet_has_no_summary(tmp_path):
    office = copy_example("returns_desk", tmp_path)
    code, out = dsl("run", ".", "--quiet", cwd=office)
    assert code == 0, out
    assert "Run summary" not in out


def test_run_names_the_problem_and_points_to_check(tmp_path):
    office = copy_example("returns_desk", tmp_path)
    md = office / "office.md"
    md.write_text(md.read_text(encoding="utf-8").replace(": clerk(", ": clerck("),
                  encoding="utf-8")
    code, out = dsl("run", ".", cwd=office)
    assert code == 1
    assert "cannot start" in out
    assert "Did you mean 'clerk'?" in out
    assert "dsl check" in out


@pytest.mark.parametrize("flag", [["--trace"], ["--resume", "latest"],
                                  ["--snapshot-interval", "5"]])
def test_run_refuses_version_1_flags(tmp_path, flag):
    office = copy_example("returns_desk", tmp_path)
    code, out = dsl("run", ".", *flag, cwd=office)
    assert code == 2
    assert "not available in this version" in out


def test_there_is_no_build_step(tmp_path):
    """The office is built in memory by every run; nothing is generated."""
    office = copy_example("returns_desk", tmp_path)
    code, out = dsl("build", ".", cwd=office)
    assert code == 2 and "invalid choice: 'build'" in out
    assert dsl("run", ".", "--quiet", cwd=office)[0] == 0
    assert not (office / "build").exists()


def test_draw_lists_kinds_and_arrows(tmp_path):
    office = copy_example("returns_desk", tmp_path)
    code, out = dsl("draw", ".", cwd=office)
    assert code == 0, out
    assert "Rex              router" in out
    assert "Rex.escalate -> Manager" in out and "Manager -> Gate.done" in out


def test_draw_mermaid_names_the_ports(tmp_path):
    office = copy_example("returns_desk", tmp_path)
    code, out = dsl("draw", ".", "--mermaid", "--raw", cwd=office)
    assert code == 0, out
    assert out.startswith("flowchart LR")
    assert "Rex -->|approve / done| Gate" in out
    assert 'Rex{{"Rex<br/><i>router</i>"}}' in out


def test_draw_shows_what_is_connected_to_nothing(tmp_path):
    office = copy_example("returns_desk", tmp_path)
    md = office / "office.md"
    md.write_text(md.read_text(encoding="utf-8").replace(
        "Rex.escalate -> Manager -> ", "Manager -> "), encoding="utf-8")
    code, out = dsl("draw", ".", cwd=office)
    assert "Manager (manager) receives nothing" in out, out


def test_roles_lists_the_built_in_roles(tmp_path):
    code, out = dsl("roles", cwd=tmp_path)
    assert code == 0, out
    assert "summarizer" in out and "(adds summary)" in out
    assert "deduplicator" in out and "Python, no model" in out


def test_show_prints_a_built_in_role(tmp_path):
    code, out = dsl("show", "summarizer", cwd=tmp_path)
    assert code == 0, out
    assert out.startswith("# ") and "out: summary" in out
    code, out = dsl("show", "jsonl_recorder", cwd=tmp_path)
    assert code == 0 and out.strip().endswith(".py")


def _debate_script(fail_on: str | None = None) -> list[dict]:
    """Three panellists who agree; a moderator who fails on ``fail_on``."""
    panel = [{"when": f"You are {who},",
              "reply": json.dumps({key: {"answer": "A", "reasoning": "r", "confidence": 0.9}})}
             for who, key in (("Qwen", "qwen"), ("GPT", "gpt"), ("Claude", "claude"))]
    bad = ([{"when": "You moderate a panel", "user_contains": fail_on,
             "reply": json.dumps({"agreement": "total", "final_answer": "A", "note": ""})}]
           if fail_on else [])
    good = {"when": "You moderate a panel",
            "reply": json.dumps({"agreement": "unanimous", "final_answer": "A", "note": ""})}
    return panel + bad + [good]


def test_a_stalled_loop_is_reported(tmp_path):
    """The moderator fails on the second problem, so the gate is never released.

    The gate holds that problem and waits on done; done comes only from
    the end of the loop, and everything on the way back is idle with
    nothing in transit. The third problem is never admitted.
    """
    office = copy_example("debate", tmp_path)
    code, out = dsl("run", ".", cwd=office, script=_debate_script(fail_on="fact-01"))
    assert code != 0, out
    report = out[out.index("Stalled:"):].splitlines()
    assert report[0].startswith("Stalled: debate::Gate holds an item it admitted"), report
    walked = "\n".join(report)
    assert "debate::Gate.done <- debate::Rex.finish: empty" in walked
    assert "1 message(s) wait unread on debate::Gate.in." in walked
    answers = (office / "debate_answers.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(answers) == 1  # only the first problem was finished


def test_a_loop_that_ends_normally_is_not_a_stall(tmp_path):
    office = copy_example("debate", tmp_path)
    code, out = dsl("run", ".", cwd=office, script=_debate_script())
    assert code == 0, out
    assert "Stalled:" not in out


def test_run_by_name_points_to_a_copy(tmp_path):
    """A gallery office is not run inside the installed package: a run
    writes its output next to office.md."""
    code, out = dsl("run", "returns_desk", cwd=tmp_path)
    assert code == 2
    assert "dsl init returns_desk my_returns_desk" in out
    assert not (EXAMPLES / "returns_desk" / "outcomes.jsonl").exists()


def test_check_by_name_reads_the_gallery_office(tmp_path):
    code, out = dsl("check", "debate", cwd=tmp_path)
    assert code == 0, out
    assert "no problems found" in out


# ── dsl check ──────────────────────────────────────────────────────────────

BROKEN = """\
sources:
    tickets: file_source(path="tickets.jsonl")
sinks:
    jsonl_recorder(path="outcomes.jsonl")
agents:
    Gate: gate(size=2)
    Clerk: clerck(limit=50)
    Rex: router(on="clerk_decision")
    Manager: manager
    Jay: unassigned
    Ed: summarizer(style="short")
connections:
    tickets -> Gate -> Clerk -> Rex
    Rex.approve -> jsonl_recorder, Gate.finished
    Rex.escalate -> Manager -> jsonl_recorder, Gate.done
    Manager.yes -> Ed -> Jay
"""

BAD_FRONT_MATTER = '''"""
---
in: text
out: decision (yes | no
---
"""
class Manager:
    def __call__(self, m):
        return m
'''


def test_check_lists_every_problem_in_line_order(tmp_path):
    office = copy_example("returns_desk", tmp_path)
    (office / "office.md").write_text(BROKEN, encoding="utf-8")
    (office / "roles" / "manager.py").write_text(BAD_FRONT_MATTER, encoding="utf-8")
    code, out = dsl("check", ".", cwd=office)
    assert code == 1
    problems = [line for line in out.splitlines() if "problem:" in line]
    expected = [
        "line 6: a gate takes no arguments",
        "line 7: no agent called 'clerck'",
        "line 9: roles/manager.py: front matter line 3",
        "line 11: an English role takes only ai=, not style",
        "line 14: Gate has inboxes in and done; it has no 'finished'",
        "line 16: Manager has one outbox, out; it has no 'yes'",
    ]
    assert len(problems) == len(expected), out
    for got, want in zip(problems, expected):
        assert want in got, (got, want)
    assert "note: line 10: Jay is unassigned" in out


def test_check_a_draft_is_not_broken(tmp_path):
    office = copy_example("org_news_filter", tmp_path)
    md = office / "office.md"
    text = md.read_text(encoding="utf-8")
    md.write_text(text.replace("agents:\n", "agents:\n    Jay: unassigned\n", 1),
                  encoding="utf-8")
    code, out = dsl("check", ".", cwd=office)
    assert code == 0, out
    assert "Jay is unassigned" in out


def test_check_does_not_construct_roles(tmp_path):
    """A role whose constructor would fail (or load a model) is not built by check."""
    office = copy_example("returns_desk", tmp_path)
    (office / "roles" / "clerk.py").write_text(
        '"""\n---\nin: amount\nout: clerk_decision (approve | escalate)\n---\n"""\n'
        "raise SystemExit('imported')\n", encoding="utf-8")
    code, out = dsl("check", ".", cwd=office)
    assert code == 0, out
    assert "imported" not in out
    code, out = dsl("run", ".", cwd=office)  # run does import it
    assert code != 0


@pytest.mark.parametrize("name", sorted(
    p.name for p in EXAMPLES.iterdir() if (p / "office.md").is_file()))
def test_check_every_example(name, tmp_path):
    office = copy_example(name, tmp_path)
    code, out = dsl("check", ".", cwd=office)
    if name == "backyard_birds" and not importlib.util.find_spec("birdnetlib"):
        assert code == 1
        assert "pip install birdnetlib" in out
    else:
        assert code == 0, out
        assert "no problems found" in out


# ── Which path ─────────────────────────────────────────────────────────────


@pytest.mark.parametrize("md", sorted(EXAMPLES.rglob("office.md")), ids=lambda p: p.parent.name)
def test_every_example_is_new_form(md):
    assert not is_old_form(md.read_text(encoding="utf-8"))


# ── Ctrl-C ─────────────────────────────────────────────────────────────────

FOREVER = '''"""
---
out: tick
---
A source that never ends.
"""
import time


class Forever:
    def __init__(self):
        self.n = 0

    def __call__(self):
        time.sleep(0.05)
        self.n += 1
        return {"tick": self.n}
'''


@pytest.mark.skipif(sys.platform == "win32", reason="SIGINT is delivered differently on Windows")
def test_ctrl_c_stops_an_office_that_would_run_for_ever(tmp_path):
    """Before: a KeyboardInterrupt traceback, and the process kept running."""
    import signal
    import time

    office = tmp_path / "forever"
    (office / "sources").mkdir(parents=True)
    (office / "sources" / "forever.py").write_text(FOREVER, encoding="utf-8")
    (office / "office.md").write_text(
        "sources:\n    ticks: forever\nsinks:\n    discard\nconnections:\n    ticks -> discard\n",
        encoding="utf-8")
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(
        [str(REPO)] + ([env["PYTHONPATH"]] if env.get("PYTHONPATH") else []))
    env["PYTHONUNBUFFERED"] = "1"
    proc = subprocess.Popen(
        [sys.executable, "-c",
         "import sys; from dissyslab.cli import main; sys.exit(main(sys.argv[1:]))", "run", "."],
        cwd=office, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    time.sleep(3)
    proc.send_signal(signal.SIGINT)
    out, _ = proc.communicate(timeout=30)
    assert proc.returncode == 130, out
    assert "Stopped (Ctrl-C)." in out
    assert "Run summary" in out and "forever::ticks" in out
    assert "Traceback" not in out
