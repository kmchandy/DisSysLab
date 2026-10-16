"""Grade a finished run: compare debate_answers.jsonl with answer_keys.jsonl.

    python grade.py

The answer keys are kept out of the office on purpose, so no model sees
them (spec 4.4: data the office does not need stays outside it).
"""

import json
from pathlib import Path


def read(path):
    return [json.loads(x) for x in Path(path).read_text().splitlines() if x.strip()]


keys = {k["problem_id"]: k["answer_key"] for k in read("answer_keys.jsonl")}
for a in read("debate_answers.jsonl"):
    key = keys.get(a["problem_id"])
    mark = "?" if key is None else ("right" if key.lower() in str(a["final_answer"]).lower()
                                    else "wrong")
    print(f"{a['problem_id']:8} {mark:5} {a['final_answer']!s:30} ({a['agreement']})")
