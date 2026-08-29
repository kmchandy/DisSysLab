# dissyslab/gallery/apps/adaptive_tutor/roles/fractions_subject.py

"""
---
inboxes: in_
outboxes: out
---
# built by register_subject_bank_role, so nothing in this module names the ports.
FRACTIONS subject -- first instance of adaptive_tutor's subject
contract (see ``_subject_common.py``). Simplest example: addition and
subtraction of two proper fractions with small denominators.

Every problem's ``correct_answer`` is *computed* with ``fractions.
Fraction`` (exact rational arithmetic), never hand-typed -- that's
what makes ``check_problem_ground_truth.py`` a real check rather than
a check against the same list it's supposed to be verifying.
"""

import os
import random
import sys
from fractions import Fraction
from typing import Any, Dict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _subject_common import register_subject_bank_role  # noqa: E402

VARIANTS: Dict[str, Dict[str, Any]] = {
    "easy": {"session_length": 4, "max_denominator": 4, "operations": ["+"]},
    "hard": {"session_length": 5, "max_denominator": 8, "operations": ["+", "-"]},
}


def _fractions_generate_problem(rng: random.Random, params: Dict[str, Any]) -> Dict[str, Any]:
    max_den = params.get("max_denominator", 4)
    ops = params.get("operations", ["+"])
    op = rng.choice(ops)

    d1 = rng.randint(2, max_den)
    n1 = rng.randint(1, d1 - 1)
    d2 = rng.randint(2, max_den)
    n2 = rng.randint(1, d2 - 1)
    f1, f2 = Fraction(n1, d1), Fraction(n2, d2)

    if op == "+":
        result = f1 + f2
        text = f"{n1}/{d1} + {n2}/{d2} = ?"
    else:
        if f1 < f2:
            f1, f2 = f2, f1  # keep subtraction non-negative
        result = f1 - f2
        text = f"{f1.numerator}/{f1.denominator} - {f2.numerator}/{f2.denominator} = ?"

    correct = (
        str(result.numerator) if result.denominator == 1
        else f"{result.numerator}/{result.denominator}"
    )
    accepted_forms = sorted({correct, f"{float(result):g}"})

    # A plausible wrong answer for STUDENT to type when scripted to miss:
    # the classic "combine numerators, combine denominators directly"
    # mistake, rather than an unrelated placeholder string. Formatted the
    # same way `correct` is, so it looks like a real fraction answer.
    if op == "+":
        mistake_num, mistake_den = f1.numerator + f2.numerator, f1.denominator + f2.denominator
    else:
        mistake_num, mistake_den = f1.numerator - f2.numerator, f1.denominator - f2.denominator
    if mistake_den == 0:
        distractor_fraction = Fraction(result.numerator + 1, result.denominator)
    else:
        distractor_fraction = Fraction(mistake_num, mistake_den)
    if distractor_fraction == result:
        distractor_fraction = Fraction(result.numerator + 1, result.denominator)
    distractor = (
        str(distractor_fraction.numerator) if distractor_fraction.denominator == 1
        else f"{distractor_fraction.numerator}/{distractor_fraction.denominator}"
    )

    return {
        "text": text,
        "correct_answer": correct,
        "accepted_forms": accepted_forms,
        "distractor": distractor,
        "grading_notes": (
            "Accept any mathematically equivalent form (an unreduced "
            "fraction, a decimal, or a spelled-out word like 'one half')."
        ),
    }


role = register_subject_bank_role("fractions", VARIANTS, _fractions_generate_problem)
