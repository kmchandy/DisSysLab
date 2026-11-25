"""Class 6 (course/Whiteboard.html) against the runs and the code it describes.

Every quotation on the page is from a note or a verdict in
course/lab2/traces/2026-11-20/, or from the attack evidence it shows; the
run table is computed from run 4; the facts it states about the runs and
the board are checked against the traces and board.py.
"""

from __future__ import annotations

import html
import importlib.util
import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PAGE = (REPO / "course" / "Whiteboard.html").read_text(encoding="utf-8")
TRACES = REPO / "course" / "lab2" / "traces" / "2026-11-20"
CAKE = REPO / "dissyslab" / "gallery" / "cake_room"


def flat(s: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", s))).strip()


TEXT = flat(PAGE)


def run(name: str) -> dict:
    lines = (TRACES / f"{name}_report.jsonl").read_text(encoding="utf-8").splitlines()
    return json.loads([ln for ln in lines if ln.strip()][-1])


RUNS = {n: run(n) for n in ["run1_mo_note", "run2_camera", "run3_covering", "run4_clean"]}


def test_the_model_is_the_one_the_traces_were_run_on():
    assert "claude-haiku-5-5" in (TRACES / "README.md").read_text(encoding="utf-8")
    assert "claude-haiku-5-5" in PAGE


def test_the_run_table_is_computed_from_run_4():
    table = re.search(r'<table class="run">(.*?)</table>', PAGE, re.S).group(1)
    rows = [[flat(c) for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", tr, re.S)]
            for tr in re.findall(r"<tr>(.*?)</tr>", table, re.S)][1:]
    expected, last = [], {}
    for n in RUNS["run4_clean"]["board"]:
        marks = (["stale"] if n["read"] < n["n"] - 1 else []) + \
                (["changes"] if n["by"] in last and last[n["by"]] != n["suspect"] else [])
        last[n["by"]] = n["suspect"]
        expected.append([str(n["n"]), n["by"], str(n["read"]), n["suspect"], ", ".join(marks)])
    assert rows == expected


def test_the_stale_count_and_the_verdicts_the_page_states():
    board = RUNS["run4_clean"]["board"]
    stale = sum(n["read"] < n["n"] - 1 for n in board)
    words = {7: "Seven", 8: "eight"}
    assert f"{words[stale]} of the {words[len(board)]} notes are stale reads" in TEXT
    assert RUNS["run4_clean"]["culprit"] == RUNS["run2_camera"]["culprit"] == "cal"
    assert RUNS["run1_mo_note"]["culprit"] == RUNS["run3_covering"]["culprit"] == "unknown"


def test_run_2_used_the_same_evidence_and_a_different_order():
    same = (TRACES / "run2_camera_evidence.jsonl").read_text(encoding="utf-8")
    assert same == (CAKE / "evidence" / "clean.jsonl").read_text(encoding="utf-8")

    def firsts(board):
        out = []
        for n in board:
            if n["by"] not in out:
                out.append(n["by"])
        return ", ".join(out)

    assert f"in the order {firsts(RUNS['run2_camera']['board'])} " \
           f"(run 4: {firsts(RUNS['run4_clean']['board'])})" in TEXT
    assert f"the board held {len(RUNS['run2_camera']['board'])} notes, " \
           f"not {len(RUNS['run4_clean']['board'])}" in TEXT


def test_where_run_3_ended():
    last = {}
    for n in RUNS["run3_covering"]["board"]:
        last[n["by"]] = n["suspect"]
    assert last == {"Pip": "unknown", "Rae": "unknown", "Quinn": "cal"}
    assert "Pip and Rae ended at unknown, Quinn at Cal" in TEXT


def test_every_quotation_is_real():
    said = [flat(n["note"]) for r in RUNS.values() for n in r["board"]]
    said += [flat(r["reason"]) for r in RUNS.values()]
    said += [flat(json.loads(ln)["text"].replace('"', ""))
             for ln in (CAKE / "evidence" / "covering.jsonl").read_text(encoding="utf-8").splitlines()]
    quotes = [flat(q) for q in re.findall(r"<blockquote(?: class=\"ok\")?>(.*?)</blockquote>", PAGE, re.S)]
    assert len(quotes) >= 5
    for q in quotes:
        assert any(q in s for s in said), q


def test_the_cap_is_the_boards():
    spec = importlib.util.spec_from_file_location("cake_board", CAKE / "roles" / "board.py")
    board = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(board)
    cap = board.Board().settings["max_notes"]
    assert f"the board takes at most {cap} notes" in TEXT
    assert sorted(board.DETECTIVES.values()) == ["Pip", "Quinn", "Rae"]


#: Quotations from published accounts (blockquote class="src"), each with
#: the page it was copied from. A test cannot fetch them; it can make sure
#: every quotation names its source and that the page links to it. Check
#: the wording against the source by hand when adding one.
OUTSIDE = {
    "hyperfocused on finding a solution for ExploitGym":
        "https://openai.com/index/hugging-face-model-evaluation-security-incident/",
    "an attempt to cheat the evaluation":
        "https://huggingface.co/blog/agent-intrusion-technical-timeline",
}


def test_every_outside_quotation_has_a_linked_source():
    quotes = [flat(q) for q in re.findall(r'<blockquote class="src">(.*?)</blockquote>', PAGE, re.S)]
    assert sorted(quotes) == sorted(OUTSIDE)
    for url in OUTSIDE.values():
        assert f'href="{url}"' in PAGE, url


def test_every_incident_names_a_source():
    section = PAGE[PAGE.index("Beyond the cake room"):PAGE.index("Questions for the class")]
    for row in re.findall(r"<tr><td><b>(.*?)</tr>", section, re.S):
        assert 'href="https://' in row, flat(row)[:40]
    for item in re.findall(r"<li><b>(.*?)</li>", section.split("<h3>Poisoned parts</h3>")[1], re.S):
        if "</ul>" in item:
            break
        assert 'href="https://' in item, flat(item)[:40]
