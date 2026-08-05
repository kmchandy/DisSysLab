# scripts/manual_checks/check_problem_ground_truth.py

"""
adaptive_tutor's analog of mac_speed_suite's check_no_lookahead.py --
an automatic, mechanical correctness check for a subject's
generate_problem function, run before wiring a new subject into
office.md.

What this checks, and why it's NOT "does the LLM think this looks
right"
========================================================================

No-lookahead (mac_speed_suite) has a clean mechanical test because its
invariant is about *time*: recompute a signal on a truncated price
history and confirm day t's value didn't change. Tutoring problems
aren't sequential in that sense, so this checker verifies the
analogous thing that *is* mechanically checkable here: does a
subject's generate_problem function's OWN claims about a problem hold
together internally, with no LLM involved in the check itself?

Four checks, each on every variant a subject declares:

1. **Self-consistency.** ``correct_answer`` must be one of the
   entries in ``accepted_forms`` -- catches the easy bug where a
   generator computes the right answer but types a different string
   into the two fields (or forgets to include the canonical form in
   its own accepted-forms list).
2. **No junk entries.** ``accepted_forms`` has no empty strings and no
   exact duplicates.
3. **Distractor is actually wrong.** If a problem provides the optional
   ``distractor`` field (a plausible-looking wrong answer for the
   scripted STUDENT to type -- see ``_subject_common.py``'s contract),
   it must NOT equal ``correct_answer`` and must NOT appear in
   ``accepted_forms``. Catches a generator whose "wrong-by-one-step"
   arithmetic silently lands back on a right answer for some inputs
   (a real risk any perturb-the-correct-answer approach runs into).
4. **Determinism.** Calling generate_problem again with a *fresh*
   ``random.Random`` seeded identically reproduces the exact same
   sequence of problems. This is the check most likely to catch a
   real bug: a generator that accidentally calls the global
   ``random.random()`` / ``random.randint()`` instead of the ``rng``
   it was given breaks ``make_subject_bank``'s reproducibility
   guarantee (see ``roles/_subject_common.py``'s docstring) silently
   -- nothing crashes, sessions just stop being replayable, exactly
   the kind of bug that "looks right" under casual inspection.

What this deliberately does NOT check: whether ``correct_answer`` is
*actually* the mathematically correct answer to the problem's own
text. That would require this checker to independently re-implement
each subject's own arithmetic, which is circular (it would just be
trusting a second copy of the same logic) -- the same reason
no-lookahead doesn't try to verify a trading signal is *profitable*,
only that it obeys its own stated causality rule. Getting the
arithmetic right is still the subject author's job; this checker
catches the class of bugs that's actually checkable without redoing
that work.

Usage:
    from check_problem_ground_truth import assert_subject_contract
    assert_subject_contract(generate_problem, variants, n_samples=30)
"""

import os
import random
import sys
from typing import Any, Callable, Dict


def assert_subject_contract(
    generate_problem: Callable[[random.Random, Dict[str, Any]], Dict[str, Any]],
    variants: Dict[str, Dict[str, Any]],
    n_samples: int = 30,
) -> None:
    """Raises AssertionError on the first violation found; returns
    silently (no exception) if every variant passes all three checks."""
    for variant_name, params in variants.items():
        seed = params.get("seed", hash(("_ground_truth_check_", variant_name)) & 0xFFFFFFFF)

        rng_a = random.Random(seed)
        problems_a = [generate_problem(rng_a, params) for _ in range(n_samples)]

        for i, problem in enumerate(problems_a):
            correct = problem.get("correct_answer")
            forms = problem.get("accepted_forms", [])
            assert correct is not None and correct != "", (
                f"[{variant_name}] problem {i}: empty correct_answer -- {problem!r}"
            )
            assert correct in forms, (
                f"[{variant_name}] problem {i}: correct_answer {correct!r} not in "
                f"its own accepted_forms {forms!r} -- {problem!r}"
            )
            assert all(f != "" for f in forms), (
                f"[{variant_name}] problem {i}: accepted_forms contains an empty string -- {forms!r}"
            )
            assert len(forms) == len(set(forms)), (
                f"[{variant_name}] problem {i}: accepted_forms has duplicate entries -- {forms!r}"
            )
            distractor = problem.get("distractor")
            if distractor:
                assert distractor != correct, (
                    f"[{variant_name}] problem {i}: distractor {distractor!r} equals "
                    f"correct_answer -- {problem!r}"
                )
                assert distractor not in forms, (
                    f"[{variant_name}] problem {i}: distractor {distractor!r} is itself "
                    f"an accepted form -- {problem!r}"
                )

        rng_b = random.Random(seed)
        problems_b = [generate_problem(rng_b, params) for _ in range(n_samples)]
        assert problems_a == problems_b, (
            f"[{variant_name}] generate_problem is not deterministic given the same "
            f"seed -- check for a call to the global random module instead of the "
            f"rng argument it was given."
        )


def main():
    sys.path.insert(
        0, os.path.join(os.path.dirname(__file__), "..", "..",
                         "dissyslab", "gallery", "apps", "adaptive_tutor", "roles")
    )
    from fractions_subject import VARIANTS as FRACTIONS_VARIANTS, _fractions_generate_problem
    from multiplication_facts_subject import (
        VARIANTS as MULT_VARIANTS, _multiplication_generate_problem,
    )
    from telling_time_subject import (
        VARIANTS as TELLING_TIME_VARIANTS, _telling_time_generate_problem,
    )

    subjects = [
        ("fractions", _fractions_generate_problem, FRACTIONS_VARIANTS),
        ("multiplication_facts", _multiplication_generate_problem, MULT_VARIANTS),
        ("telling_time", _telling_time_generate_problem, TELLING_TIME_VARIANTS),
    ]

    all_ok = True
    for name, fn, variants in subjects:
        try:
            assert_subject_contract(fn, variants)
            print(f"PASS: {name} ({len(variants)} variant(s))")
        except AssertionError as exc:
            all_ok = False
            print(f"FAIL: {name}: {exc}")

    print()
    print("ALL SUBJECTS PASSED" if all_ok else "SOME SUBJECTS FAILED")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
