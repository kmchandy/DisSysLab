# dissyslab/gallery/apps/adaptive_tutor/roles/multiplication_facts_subject.py

"""
---
inboxes: in_
outboxes: out
---
# built by register_subject_bank_role, so nothing in this module names the ports.
MULTIPLICATION_FACTS subject -- second instance of adaptive_tutor's
subject contract, added to prove the shared PLANNER/CHECKER/STUDENT
machinery genuinely needs zero changes for a second subject (see
_subject_common.py).

Deliberate contrast with fractions_subject.py: a multiplication fact
has exactly one correct numeric form -- no fraction/decimal/word
equivalence to accept. ``accepted_forms`` is a single-element list,
and ``grading_notes`` says so explicitly, which is itself a small but
real test of the contract: CHECKER's shared LLM-grading code doesn't
need to know or care that this subject's equivalence rule is "none" --
it just follows whatever ``grading_notes`` says, same as it follows
fractions' "accept equivalent forms" instruction.
"""

import os
import random
import sys
from typing import Any, Dict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _subject_common import register_subject_bank_role  # noqa: E402

VARIANTS: Dict[str, Dict[str, Any]] = {
    "easy": {"session_length": 4, "max_factor": 5},
    "hard": {"session_length": 5, "max_factor": 12},
}


def _multiplication_generate_problem(rng: random.Random, params: Dict[str, Any]) -> Dict[str, Any]:
    max_factor = params.get("max_factor", 5)
    a = rng.randint(2, max_factor)
    b = rng.randint(2, max_factor)
    product = a * b

    # Plausible wrong answer for STUDENT to type when scripted to miss:
    # the real product of the wrong-by-one fact a x (b+1) -- a genuine
    # multiplication result, always different from `product` (they
    # differ by exactly `a`), not an unrelated placeholder string.
    distractor = str(a * (b + 1))

    return {
        "text": f"{a} x {b} = ?",
        "correct_answer": str(product),
        "accepted_forms": [str(product)],
        "distractor": distractor,
        "grading_notes": (
            "There is exactly one correct numeric answer for a "
            "multiplication fact -- do not accept any other form."
        ),
    }


role = register_subject_bank_role(
    "multiplication_facts", VARIANTS, _multiplication_generate_problem,
)
