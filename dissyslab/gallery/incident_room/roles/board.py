"""
---
emits: the whiteboard: hands out the evidence, collects notes, and gives the writer the board
kind: author
out: to (logs | metrics | reports | writer), incident, board
out if to is logs: round, evidence
out if to is metrics: round, evidence
out if to is reports: round, evidence
---
Arguments: rounds -- how many times each analyst writes on the board
(default 2).

The whiteboard. Every note an analyst writes goes on it, and every analyst
reads all of it before writing again. That is its power: an analyst can
build on what the others found. It is also its weakness: whatever one
analyst writes, every other analyst and the writer will read.

It receives two kinds of message on its one inbox: a piece of evidence
from the source (it has "kind") and an analyst's message back (it has
"note"). When all three pieces of evidence are in, it starts round 1:
each analyst gets its own evidence and the board, still empty. When all
three notes of a round are in, it starts the next round, with the whole
board; after the last round it gives the board to the writer.
"""

ANALYSTS = ["logs", "metrics", "reports"]


def step(item, state, settings):
    """(messages to send, new state). All of the board's logic is here."""
    if "note" in item:  # an analyst's message back: it still has "to" and "round"
        note = {"by": item["to"], "round": item["round"], "note": item["note"]}
        state["board"].append(note)
        done = [n for n in state["board"] if n["round"] == item["round"]]
        if len(done) < len(ANALYSTS):
            return [], state
        if item["round"] < settings["rounds"]:
            return deal(item["round"] + 1, state), state
        return [{"to": "writer", "incident": state["incident"],
                 "board": state["board"]}], state

    state["evidence"][item["kind"]] = item["text"]  # a piece of evidence
    state["incident"] = item["incident"]
    if len(state["evidence"]) < len(ANALYSTS):
        return [], state
    return deal(1, state), state


def deal(round_no, state):
    """One message per analyst: its own evidence, and the board so far."""
    return [{"to": who, "incident": state["incident"], "round": round_no,
             "evidence": state["evidence"][who], "board": list(state["board"])}
            for who in ANALYSTS]


class Board:
    def __init__(self, rounds=2):
        self.settings = {"rounds": rounds}
        self.state = {"incident": None, "evidence": {}, "board": []}

    def __call__(self, item):
        out, self.state = step(item, self.state, self.settings)
        return out
