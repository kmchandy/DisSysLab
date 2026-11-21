"""
---
emits: the whiteboard: sends itself to the detectives whenever it changes, and gives the judge the board when nobody has more to say
kind: author
out: to (door | shop | fridge | judge), case, board
out if to is door: evidence
out if to is shop: evidence
out if to is fridge: evidence
---
Arguments: max_notes -- the most notes the board will take (default 12).
After that it stops taking notes, so a run cannot go on for ever.

The whiteboard. It does nothing on its own: it changes only when a
detective writes on it, and whenever it changes, every detective who has
not seen the change is sent the board as it is now. Nobody waits for
anybody: other notes may arrive while a detective is still reading.

It receives two kinds of message on its one inbox: a piece of evidence
from the source (it has "kind"), and a detective's reply to the board it
was sent (it has "post").

- When all three pieces of evidence are in, it sends each detective its
  own evidence and the board, still empty.
- A reply with "post": "yes" adds a note to the board. "post": "no"
  changes nothing. A note records "read": how many notes were on the
  board its writer read. If the note's "n" is more than "read" + 1,
  other notes arrived while its writer was thinking: it wrote without
  having read them.
- After every reply, each detective who is not busy, and has not yet
  seen a note someone else wrote, is sent the board as it is now.
- A detective who is busy (it has a copy it has not answered) is not
  sent another one. When its reply comes in, its note is on the board
  first, then it gets the newest board if that has anything it has not
  seen. A detective therefore never reads a board without its own last
  note: it has no memory but the board, and a board that lagged behind
  would make it write the same note again.
- When no detective is busy, every one has read every note the others
  wrote and had nothing more to add, so nothing will ever be written
  again. Only then does the judge get the board.

If a detective's call fails (the model service errors), its reply never
comes back, it stays busy, and the run ends with no verdict.
"""

DETECTIVES = {"door": "Pip", "shop": "Quinn", "fridge": "Rae"}


def step(item, state, settings):
    """(messages to send, new state). All of the board's logic is here."""
    if "post" not in item:  # a piece of evidence
        state["evidence"][item["kind"]] = item["text"]
        state["case"] = item["case"]
        if len(state["evidence"]) < len(DETECTIVES):
            return [], state
        return [send(d, state) for d in DETECTIVES], state

    # A detective's reply: it still carries "to", saying who it was.
    state["busy"].remove(item["to"])
    if item["post"] == "yes" and len(state["board"]) < settings["max_notes"]:
        state["board"].append({"n": len(state["board"]) + 1,
                               "by": DETECTIVES[item["to"]],
                               "read": state["seen"][item["to"]],
                               "note": item["note"], "suspect": item["suspect"]})
    out = [send(d, state) for d in DETECTIVES
           if d not in state["busy"] and has_news(d, state)]
    if not state["busy"]:
        out.append({"to": "judge", "case": state["case"], "board": list(state["board"])})
    return out, state


def has_news(d, state):
    """Has someone other than d written since d was last sent the board?"""
    return any(n["n"] > state["seen"][d] and n["by"] != DETECTIVES[d]
               for n in state["board"])


def send(d, state):
    """The board as it is now, for detective d, who is busy until it replies."""
    state["busy"].add(d)
    state["seen"][d] = len(state["board"])
    return {"to": d, "case": state["case"], "evidence": state["evidence"][d],
            "board": list(state["board"])}


class Board:
    def __init__(self, max_notes=12):
        self.settings = {"max_notes": max_notes}
        self.state = {"case": None, "evidence": {}, "board": [],
                      "busy": set(), "seen": {d: 0 for d in DETECTIVES}}

    def __call__(self, item):
        out, self.state = step(item, self.state, self.settings)
        return out
