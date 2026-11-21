"""End-to-end: Lab 2's cake room, with the model scripted.

The board is event-driven (roles/board.py; its logic is tested on its own
in tests/unit/test_cake_board.py). This runs the whole office with
`dsl run`, threads and all, and checks that it reaches a verdict: the
detectives write, the board sends itself on, the detectives go quiet, and
Judy gets the board once.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from tests.e2e.test_lab_paths import lines_of, run_office

REPO = Path(__file__).resolve().parents[2]
CAKE = REPO / "dissyslab" / "gallery" / "cake_room"


def office(tmp_path: Path, evidence: str = "clean") -> Path:
    dst = tmp_path / "lab2"
    shutil.copytree(CAKE, dst, ignore=shutil.ignore_patterns(
        "__pycache__", "trials.jsonl", "report.jsonl", "refused.jsonl"))
    shutil.copyfile(dst / "evidence" / f"{evidence}.jsonl", dst / "evidence.jsonl")
    return dst


def reply(post: bool, note: str = "", suspect: str = "unknown") -> str:
    return json.dumps({"post": "yes" if post else "no", "note": note, "suspect": suspect})


def detective(name: str, clears: str) -> list[dict]:
    """Writes once with what its own evidence shows; once all three notes are
    on the board, writes again naming Cal; then has nothing more to say."""
    return [
        {"when": f"You are {name}", "user_contains": [f"Cal, says {name}"],
         "reply": reply(False)},
        {"when": f"You are {name}", "user_contains": ['"by": "Pip"', '"by": "Quinn"', '"by": "Rae"'],
         "reply": reply(True, f"Cal, says {name}: the others cleared the rest.", "cal")},
        {"when": f"You are {name}", "user_contains": [f'"by": "{name}"'], "reply": reply(False)},
        {"when": f"You are {name}", "reply": reply(True, f"{clears} is cleared.")},
    ]


TEAM = detective("Pip", "Dee") + detective("Quinn", "Ben") + detective("Rae", "Ann") + [
    {"when": "You are Judy", "user_contains": "the others cleared the rest",
     "reply": json.dumps({"culprit": "cal", "reason": "The board clears the other three."})},
    {"when": "You are Judy", "reply": json.dumps({"culprit": "unknown", "reason": "Not enough."})},
]


def test_the_office_reaches_one_verdict(tmp_path):
    lab = office(tmp_path)
    code, out, calls = run_office(lab, TEAM)
    assert code == 0, out
    reports = lines_of(lab / "report.jsonl")
    assert len(reports) == 1, out
    assert reports[0]["culprit"] == "cal"
    board = reports[0]["board"]
    assert [n["n"] for n in board] == list(range(1, len(board) + 1))
    for name in ("Pip", "Quinn", "Rae"):
        mine = [n for n in board if n["by"] == name]
        assert 1 <= len(mine) <= 2, (name, board)
    assert sum(1 for c in calls if "You are Judy" in c["when"]) == 1


def posts(name: str, board: list[dict]) -> bool:
    """What detective() above replies to this board: does it write?"""
    mine = [n for n in board if n["by"] == name]
    if any(n["note"].startswith("Cal") for n in mine):
        return False
    if {n["by"] for n in board} == {"Pip", "Quinn", "Rae"}:
        return True
    return not mine


def test_no_detective_is_sent_a_board_without_its_own_note(tmp_path):
    """It has no memory but the board: a board without its last note would
    make it write that note again."""
    lab = office(tmp_path)
    _, out, calls = run_office(lab, TEAM)
    for name in ("Pip", "Quinn", "Rae"):
        seen = [json.loads(c["user"])["board"] for c in calls if f"You are {name}" in c["when"]]
        assert seen and seen[0] == [], (name, out)
        for before, after in zip(seen, seen[1:]):
            own = lambda b: sum(n["by"] == name for n in b)
            assert own(after) == own(before) + posts(name, before), (name, before, after)
