"""The Lab 2 handout (course/lab2.html) against what runs.

Every file it prints is the gallery's or the reference design's; every
line of output it prints is what dsl, grade.py or trials.py print; the
Claude-track script at least parses (it is marked untested on the page).
"""

from __future__ import annotations

import ast
import html
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

from tests.e2e import test_incident_room as room
from tests.e2e.test_lab_paths import run_office

REPO = Path(__file__).resolve().parents[2]
PAGE = (REPO / "course" / "lab2.html").read_text(encoding="utf-8")
GALLERY = REPO / "dissyslab" / "gallery" / "incident_room"
HERE = Path(__file__).resolve().parent


def files() -> dict[str, str]:
    return {name: html.unescape(body) for name, body in
            re.findall(r'<pre data-file="([^"]+)">(.*?)</pre>', PAGE, re.S)}


def outputs() -> list[str]:
    return [html.unescape(b) for b in re.findall(r'<pre class="out">(.*?)</pre>', PAGE, re.S)]


def output_starting(prefix: str) -> str:
    found = [b for b in outputs() if b.startswith(prefix)]
    assert len(found) == 1, prefix
    return found[0]


def code_lines(text: str) -> list[str]:
    return [ln for ln in text.splitlines() if ln.strip() and not ln.lstrip().startswith("#")]


def test_the_starter_files_on_the_page_are_the_gallery_files():
    shown = files()
    for name in ("office.md", "roles/reports_analyst.md", "roles/incident_writer.md"):
        assert shown[name].strip() == (GALLERY / name).read_text(encoding="utf-8").strip(), name


def test_the_design_files_on_the_page_are_the_reference_designs():
    shown = files()
    pipeline = HERE / "incident_room_pipeline"
    assert shown["roles/reports_finding.md"].strip() == \
        (pipeline / "roles" / "reports_finding.md").read_text(encoding="utf-8").strip()
    assert shown["roles/reports_analyst.md (design C)"].strip() == \
        (HERE / "incident_room_guarded" / "roles" / "reports_analyst.md").read_text(encoding="utf-8").strip()
    office_b = output_starting("# incident_room, design B")
    assert code_lines(office_b) == code_lines((pipeline / "office.md").read_text(encoding="utf-8"))
    out_line = output_starting("out: incident, suspect").strip()
    for role in ("logs_finding.md", "metrics_finding.md"):
        assert out_line in (pipeline / "roles" / role).read_text(encoding="utf-8").splitlines(), role


def test_the_dsl_check_output_is_real(tmp_path):
    from tests.e2e.test_refused_outbox import dsl

    lab = room.office(tmp_path)
    assert dsl("check", ".", cwd=lab).strip() == output_starting("lab2/office.md:").strip()


def grade_output(lab: Path) -> str:
    done = subprocess.run([sys.executable, "grade.py"], cwd=lab, capture_output=True, text=True)
    return done.stdout


def test_the_grader_output_on_the_page_is_what_it_prints(tmp_path):
    lab = room.office(tmp_path / "clean", clean=True)
    run_office(lab, room.HONEST)
    assert grade_output(lab).strip() == output_starting("root cause: deploy").strip()
    lab = room.office(tmp_path / "attacked")
    run_office(lab, room.GULLIBLE_BOARD)
    assert grade_output(lab).strip() == output_starting("root cause: unknown").strip()


def test_the_stop_on_the_page_is_what_design_c_prints(tmp_path):
    lab = tmp_path / "lab2c"
    shutil.copytree(room.office(tmp_path / "base", "incident_room_guarded"), lab)
    code, out, _ = run_office(lab, room.GULLIBLE_BOARD)
    assert code != 0
    assert output_starting("  Stopped:").strip() in out
    assert "No report: the office stopped before the writer ran. Read refused.jsonl." in grade_output(lab)
    assert "No report: the office stopped before the writer ran." in PAGE


def test_trials_runs_any_command_and_prints_the_summary_on_the_page(tmp_path):
    lab = room.office(tmp_path)
    report = {"root_cause": "deploy", "action": "rollback", "summary": "Roll back v2.3.1.", "board": []}
    writer = tmp_path / "one_run.py"
    writer.write_text(f"open('report.jsonl', 'w').write({json.dumps(json.dumps(report))})\n",
                      encoding="utf-8")
    done = subprocess.run([sys.executable, "trials.py", "--runs", "2", "--label", "A attacked",
                           "--command", f'"{sys.executable}" "{writer}"'],
                          cwd=lab, capture_output=True, text=True, timeout=60)
    assert done.returncode == 0, done.stderr
    page_lines = output_starting("A attacked: 10 runs").splitlines()
    got = done.stdout.split("A attacked: 2 runs\n", 1)[1].splitlines()
    assert len(got) == len(page_lines) - 1
    for shown, printed in zip(page_lines[1:], got):
        assert printed.startswith(shown.split("...")[0]), (shown, printed)
    assert "found the cause (quality 1): 2 of 2" in done.stdout
    assert len((lab / "trials.jsonl").read_text(encoding="utf-8").splitlines()) == 2


def test_the_claude_track_script_parses_and_writes_what_grade_reads():
    source = files()["claude_room.py"]
    tree = ast.parse(source)
    names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
    assert {"query", "ClaudeAgentOptions", "AgentDefinition", "ResultMessage"} <= names
    assert '"report.jsonl"' in source and 'report["board"] = BOARD' in source
    assert "Untested by the course staff" in PAGE
