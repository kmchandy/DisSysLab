# dissyslab/gallery/apps/adaptive_tutor/roles/scripted_student.py

"""
STUDENT -- a scripted stand-in for a real learner, so this office runs
to completion deterministically via `dsl run` with no live terminal
(the same reason mac_speed_suite/salton_sea_dashboard use recorded/
synthetic data instead of requiring a live feed). Shared, subject-
agnostic machinery: it answers using whatever ground truth PLANNER
hands it in the "ask" message, alternating a correct answer (in an
*alternate* accepted form, to actually exercise CHECKER's equivalence
judgment rather than a literal string match) with a deliberately wrong
one, by problem index -- no subject-specific knowledge baked in here.

A real deployment would swap this for a live terminal/UI worker (see
the pre-DisSysLab prototype's TERMINAL for that
shape) without touching PLANNER, BANK, or CHECKER.

Input:  {"kind": "ask", "index": 0, "text": "...",
         "correct_answer": "3/4", "accepted_forms": ["3/4", "0.75"],
         "distractor": "3/6"}
Output: {"kind": "answer", "index": 0, "given": "0.75"}

On a scripted miss, STUDENT types whatever subject-specific
``distractor`` the problem came with -- a real-looking wrong answer
(e.g. "3/6" for a fractions problem), computed by that subject's own
``generate_problem`` the same way ``correct_answer`` is (see
``_subject_common.py``'s contract). STUDENT itself still has zero
subject-specific knowledge; it just reads whichever plausible wrong
answer the subject already computed, instead of inventing one.
"""

from typing import Any, Dict

from dissyslab.blocks.role import Role
from dissyslab.office.library import AgentRoleEntry


def make_scripted_student():
    def scripted_student(msg: Dict[str, Any]):
        if msg.get("kind") != "ask":
            return []
        idx = msg.get("index", 0)
        forms = msg.get("accepted_forms") or [msg.get("correct_answer", "")]
        if idx % 2 == 0:
            given = forms[-1]  # correct, in an alternate form -- tests equivalence grading
        else:
            # Deliberately wrong -- use the subject's own plausible-looking
            # near-miss if it provided one; only fall back to a generic
            # placeholder for a subject that hasn't been updated to supply
            # "distractor" yet (see _subject_common.py's contract).
            given = msg.get("distractor") or "not sure"
        return [({"kind": "answer", "index": idx, "given": given}, "out")]

    return scripted_student


role = AgentRoleEntry(
    name="scripted_student",
    in_ports=("in_",),
    out_ports=("out",),
    factory=lambda: Role(fn=make_scripted_student(), statuses=["out"]),
)
