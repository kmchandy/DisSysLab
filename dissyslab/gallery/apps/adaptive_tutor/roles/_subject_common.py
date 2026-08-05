# dissyslab/gallery/apps/adaptive_tutor/roles/_subject_common.py

"""
Shared subject-bank contract for adaptive_tutor -- the tutoring
equivalent of mac_speed_suite's ``_signal_common.py``.

Why this exists
================

adaptive_tutor's PLANNER, CHECKER, and PARENT_REPORT never need to
know which subject a session is practicing. Only one piece varies
between subjects: how to generate one practice problem and its ground
truth. This module is the shared 3-part contract that makes that true
-- write the one small subject-specific piece, get everything else
for free, exactly the same relationship
``_signal_common.make_signal_computer`` has to ``mac_signal.py``/
``donchian_signal.py``/``turtle_signal.py`` in mac_speed_suite.

The 3 parts (see ``roles/fractions_subject.py`` for a worked example):

1. **A ``VARIANTS`` dict** -- difficulty tiers (or skill tags) this
   subject offers, e.g. ``{"easy": {...}, "hard": {...}}``. Mirrors
   MAC's five speeds / Donchian's two window lengths.

2. **A ``generate_problem(rng, params) -> dict`` function** -- given a
   seeded ``random.Random`` and this variant's params, return exactly
   one problem:
       {
           "text":           "1/2 + 1/4 = ?",
           "correct_answer": "3/4",
           "accepted_forms": ["3/4", "0.75", "three quarters"],
           "distractor":     "3/6",
           "grading_notes":  "Accept any mathematically equivalent form.",
       }
   ``correct_answer`` must be computed by this function, not
   hand-typed into a fixed list -- that's what makes the ground-truth
   check in ``check_problem_ground_truth.py`` meaningful (see that
   file's docstring). ``accepted_forms`` and ``grading_notes`` feed
   the shared CHECKER's one LLM call; CHECKER itself never changes
   per subject, only the text it's given to work with does -- same
   role EVALUATOR plays for BACKTESTER's per-variant results.
   ``distractor`` is a plausible-*looking* wrong answer, computed the
   same way ``correct_answer`` is (never a subject-agnostic placeholder
   string) -- it's what the shared, scripted STUDENT worker types when
   it's scripted to miss, so a session transcript shows a real-looking
   wrong attempt (e.g. "3/6") rather than literal text like "not the
   answer". Optional for backward compatibility, but every subject
   shipped in this office provides one; see ``fractions_subject.py``,
   ``multiplication_facts_subject.py``, and ``telling_time_subject.py``
   for three different ways to compute a plausible near-miss.

3. **This module's ``make_subject_bank`` factory** -- wraps 1+2 into
   the uniform worker body BANK actually runs. Nothing above this
   line needs to know a subject exists.

Message shape ``make_subject_bank`` produces, in one reply to
PLANNER's ``{"kind": "start_session", "variant": <name>}`` (the whole
session's problems generated up front, not served one at a time --
same "compute the whole thing once, hand it off" shape
SIGNAL_COMPUTER uses for a ticker's full price history):
    {
        "kind":     "session_bank",
        "subject":  "fractions",
        "variant":  "easy",
        "problems": [
            {"text": "1/2 + 1/4 = ?", "correct_answer": "3/4",
             "accepted_forms": ["3/4", "0.75", "three quarters"],
             "grading_notes": "Accept any mathematically equivalent form."},
            ...
        ],
    }

Design notes:
    - Problems are generated once per session, up front, with a fixed
      seed derived from ``(subject_name, variant_name, seed)`` --
      deterministic and reproducible, same convention
      ``SyntheticStockHistorySource`` uses for its ``seed`` argument.
    - ``session_length`` (how many problems per session) is a
      ``VARIANTS``-level parameter, not hardcoded here, so a subject
      can offer a short "warm-up" variant and a longer "full session"
      variant without touching this file.
"""

import random
from typing import Any, Callable, Dict, List, Optional

from dissyslab.blocks.role import Role
from dissyslab.office.library import AgentRoleEntry


def make_subject_bank(
    subject_name: str,
    variants: Dict[str, Dict[str, Any]],
    generate_problem: Callable[[random.Random, Dict[str, Any]], Dict[str, Any]],
):
    """
    Build BANK's worker body for one subject.

    Args:
        subject_name:     e.g. "fractions", "multiplication_facts".
        variants:         {variant_name: params} -- each params dict
                           must include "session_length" (int) and
                           whatever generate_problem needs; a "seed"
                           key is optional (default: derived from
                           subject_name + variant_name for
                           reproducibility without repeating every
                           session).
        generate_problem: subject-specific piece -- see this module's
                           docstring for the contract.

    Returns a `fn(msg) -> [(out_msg, "out")]` closure, wrapped by the
    caller in `Role(fn=..., statuses=["out"])`.
    """
    def bank(msg: Dict[str, Any]):
        kind = msg.get("kind")
        if kind != "start_session":
            return [(
                {"kind": "error", "error": f"BANK({subject_name}) got unexpected kind {kind!r}"},
                "out",
            )]

        variant_name = msg.get("variant", next(iter(variants)))
        if variant_name not in variants:
            return [(
                {"kind": "error",
                 "error": f"BANK({subject_name}): unknown variant {variant_name!r}, "
                          f"known: {list(variants)}"},
                "out",
            )]
        params = variants[variant_name]
        session_length = params.get("session_length", 5)
        seed = params.get("seed", hash((subject_name, variant_name)) & 0xFFFFFFFF)
        rng = random.Random(seed)

        problems: List[Dict[str, Any]] = [
            generate_problem(rng, params) for _ in range(session_length)
        ]

        return [(
            {"kind": "session_bank", "subject": subject_name, "variant": variant_name,
             "problems": problems},
            "out",
        )]

    return bank


def register_subject_bank_role(subject_name: str, variants, generate_problem):
    """Convenience for a subject's role file's `role = ...` line."""
    return AgentRoleEntry(
        name=f"{subject_name}_bank",
        in_ports=("in_",),
        out_ports=("out",),
        factory=lambda: Role(
            fn=make_subject_bank(subject_name, variants, generate_problem),
            statuses=["out"],
        ),
    )
