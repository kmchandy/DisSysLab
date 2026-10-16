"""
---
emits: the debate's final record, or the message for the next round
kind: author
in: problem_id, problem, round, history, qwen, gpt, claude, agreement, final_answer, note
out: next (finish | continue), problem_id, problem, history
out if next is finish: final_answer, agreement, rounds_used
out if next is continue: round
---
Arguments: max_rounds -- the most rounds a debate may use (default 2).

The models judge; Python keeps the rules. The round limit is here, not in
any prompt.
"""

PANEL = ["qwen", "gpt", "claude"]


def step(item, settings):
    this_round = {"round": item["round"], "note": item["note"]}
    for name in PANEL:
        this_round[name] = item[name]
    history = item["history"] + [this_round]
    rounds_used = item["round"] + 1

    if item["agreement"] != "none" or rounds_used >= settings["max_rounds"]:
        return [{
            "next": "finish",
            "problem_id": item["problem_id"],
            "problem": item["problem"],
            "history": history,
            "final_answer": item["final_answer"],
            "agreement": item["agreement"] if item["agreement"] != "none" else "timeout",
            "rounds_used": rounds_used,
        }]
    return [{
        "next": "continue",
        "problem_id": item["problem_id"],
        "problem": item["problem"],
        "history": history,
        "round": rounds_used,
    }]


class Referee:
    def __init__(self, max_rounds=2):
        self.settings = {"max_rounds": max_rounds}

    def __call__(self, item):
        return step(item, self.settings)
