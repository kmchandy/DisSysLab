"""The cake room's whiteboard (Lab 2), driven by scripted detectives.

The board is event-driven: whenever a note is added it sends itself to
the other detectives, and it gives the judge the board when every copy it
sent has been answered. These tests deliver messages in many random
orders -- each channel first-in first-out, as in a DSL office, but the
channels interleaved at random, as threads do -- and check, every time:

- the judge gets the board exactly once, and nothing is sent after it;
- every detective has answered a copy of the board holding every note
  the others wrote (so nobody is left behind with an old version);
- no detective is ever sent a board without its own last note (it has
  no memory but the board, and would write the same note again);
- the board never holds more than max_notes, even if detectives never
  stop writing.
"""

from __future__ import annotations

import importlib.util
import random
from collections import deque
from pathlib import Path

import pytest

BOARD = Path(__file__).resolve().parents[2] / "dissyslab" / "gallery" / "cake_room" / "roles" / "board.py"
EVIDENCE = [
    {"case": "cake", "kind": "door", "text": "door log"},
    {"case": "cake", "kind": "shop", "text": "receipts"},
    {"case": "cake", "kind": "fridge", "text": "fridge notes"},
]


def load():
    spec = importlib.util.spec_from_file_location("cake_board", BOARD)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# Detective behaviours: (who I am, the board I was sent, rng) -> post?

def once(me, board, rng):
    """Writes one note, then never again."""
    return not any(n["by"] == me for n in board)


def answers_news(me, board, rng):
    """Writes first, then sometimes again when someone else has written since."""
    mine = [n["n"] for n in board if n["by"] == me]
    if not mine:
        return True
    news = any(n["n"] > max(mine) and n["by"] != me for n in board)
    return news and rng.random() < 0.5


def chatty(me, board, rng):
    """Always writes: only the cap stops it."""
    return True


def run(behaviour, seed, max_notes=12):
    mod = load()
    names = mod.DETECTIVES
    rng = random.Random(seed)
    board = mod.Board(max_notes=max_notes)
    to_board = deque()                               # the board's one inbox
    to_det = {d: deque() for d in names}             # each detective's inbox
    judged, last_seen = [], {d: None for d in names}
    posted = {d: 0 for d in names}

    for e in EVIDENCE:
        to_board.append(e)
    steps = 0
    while to_board or any(to_det.values()):
        steps += 1
        assert steps < 10_000, "the office never went quiet"
        ready = (["board"] if to_board else []) + [d for d in names if to_det[d]]
        who = rng.choice(ready)
        if who == "board":
            for msg in board(to_board.popleft()):
                assert not judged, "the board sent something after the verdict"
                if msg["to"] == "judge":
                    judged.append(msg["board"])
                else:
                    to_det[msg["to"]].append(msg)
        else:
            msg = to_det[who].popleft()
            last_seen[who] = msg["board"]
            mine = sum(n["by"] == names[who] for n in msg["board"])
            if len(msg["board"]) < max_notes:  # a full board refuses notes
                assert mine == posted[who], \
                    f"seed {seed}: {names[who]} was sent a board without its own note"
            post = behaviour(names[who], msg["board"], rng)
            posted[who] += post
            to_board.append({**msg, "post": "yes" if post else "no",
                             "note": f"note by {names[who]}" if post else "",
                             "suspect": "unknown"})
    return names, judged, last_seen


@pytest.mark.parametrize("behaviour", [once, answers_news, chatty])
def test_judge_gets_the_board_once_and_last(behaviour):
    for seed in range(400):
        names, judged, last_seen = run(behaviour, seed)
        assert len(judged) == 1, f"seed {seed}: judge got the board {len(judged)} times"
        final = judged[0]
        for d, name in names.items():
            others = {n["n"] for n in final if n["by"] != name}
            seen = {n["n"] for n in last_seen[d]}
            assert others <= seen, f"seed {seed}: {name} never saw notes {others - seen}"


def test_once_gives_one_note_each():
    for seed in range(100):
        names, judged, _ = run(once, seed)
        assert sorted(n["by"] for n in judged[0]) == sorted(names.values())


def test_the_cap_stops_a_chatty_board():
    for seed in range(100):
        _, judged, _ = run(chatty, seed, max_notes=5)
        assert len(judged[0]) == 5


def test_order_of_arrival_changes_what_is_read():
    """The point of the lab: the same detectives, different timing, different boards."""
    firsts = {run(once, seed)[1][0][0]["by"] for seed in range(50)}
    assert len(firsts) > 1


def test_read_says_how_many_notes_the_writer_had_read():
    """A note's "read" is the length of the board its writer was sent:
    never more than the notes before it, and less when others landed
    while it was thinking (a stale read, which the lab asks students to find)."""
    stale = 0
    for seed in range(200):
        _, judged, _ = run(answers_news, seed)
        for note in judged[0]:
            assert 0 <= note["read"] <= note["n"] - 1, note
            stale += note["read"] < note["n"] - 1
    assert stale > 0
