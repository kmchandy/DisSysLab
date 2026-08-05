# dissyslab/gallery/apps/adaptive_tutor/roles/answer_checker.py

"""
CHECKER -- shared, subject-agnostic grading machinery. This is the
adaptive_tutor analog of mac_speed_suite's BACKTESTER/EVALUATOR: every
subject (fractions, multiplication_facts, ...) routes through this
same worker, unchanged, because the subject-specific piece
(``correct_answer``, ``accepted_forms``, ``grading_notes``) always
arrives already computed inside the message -- see
``_subject_common.py``'s contract.

CHECKER's one job: given a question, its ground truth, and what the
student typed, ask an LLM to judge equivalence (accepting reasonable
alternate forms -- "one half", "0.5", "2/4" for "1/2") and write one
short, kind sentence of feedback. This is deliberately the one place
in the office where an LLM's judgment (not a hard rule) decides
correctness -- free-text answer matching genuinely needs it, the same
way mac_speed_suite's contract deliberately keeps EVALUATOR's stats
computation LLM-free because that part doesn't need judgment. See
``check_problem_ground_truth.py`` for the automatic check that keeps
this LLM step honest: it never asks the LLM whether a problem's own
correct_answer is right, only whether a given student answer matches
an already-verified ground truth.

Input message shape (from PLANNER, one self-contained request --
no waiting on a separate "key" message, unlike the older
phase2_demo/tutor_multi.py this office replaces):
    {
        "kind":           "grade",
        "text":           "1/2 + 1/4 = ?",
        "correct_answer": "3/4",
        "accepted_forms": ["3/4", "0.75"],
        "grading_notes":  "Accept any mathematically equivalent form...",
        "given":          "three quarters",
    }

Output (``given`` is echoed straight back from the input so downstream
worker/display code -- e.g. tutor_planner.py's results list,
sinks/tutor_session_display.py -- can show what the student actually
typed alongside the verdict, without PLANNER needing to remember it
itself across the "answer" -> "graded" round trip):
    {"kind": "graded", "correct": true, "feedback": "Nice work!", "given": "three quarters"}
"""

import json
import re
from typing import Any, Dict

from dissyslab.backends import get_backend
from dissyslab.blocks.role import Role
from dissyslab.office.library import AgentRoleEntry

_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)
_BRACE_RE = re.compile(r"\{.*\}", re.DOTALL)


def _parse_json_tolerant(raw: str) -> Dict[str, Any]:
    """Tolerant JSON extractor: strips code fences, falls back to the
    first {...} blob in the text. Same spirit as the old phase2_demo/
    llm_worker.py's _parse_send, rewritten here since the current
    framework has no standalone equivalent to import (confirmed by
    checking dissyslab/components/transformers/ai_agent.py, whose own
    inline fence-stripper doesn't handle prose-wrapped JSON)."""
    text = raw.strip()
    fence = _FENCE_RE.search(text)
    if fence:
        text = fence.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    brace = _BRACE_RE.search(text)
    if brace:
        try:
            return json.loads(brace.group(0))
        except json.JSONDecodeError:
            pass
    return {}


def make_answer_checker(backend_name: str = "claude_precise"):
    def answer_checker(msg: Dict[str, Any]):
        question_text = msg.get("text", "")
        correct_answer = msg.get("correct_answer", "")
        accepted_forms = msg.get("accepted_forms", [])
        grading_notes = msg.get("grading_notes", "")
        given = msg.get("given", "")

        system = (
            "You are a warm, encouraging tutor for a child. You are given a "
            "question, its correct answer and other accepted equivalent "
            "forms, subject-specific grading notes, and what the child "
            f"typed. {grading_notes} Decide if the child is right, and "
            "write ONE short, kind sentence of feedback (a gentle hint if "
            "wrong; do NOT give away the answer on a first miss). Reply "
            'with ONLY a JSON object: {"correct": true or false, '
            '"feedback": "<one short sentence>"}.'
        )
        user = (
            f"Question: {question_text}\n"
            f"Correct answer: {correct_answer}\n"
            f"Other accepted forms: {accepted_forms}\n"
            f"Child typed: {given!r}"
        )
        raw = get_backend(backend_name).complete(system=system, user=user, max_tokens=120)
        obj = _parse_json_tolerant(raw)
        correct = bool(obj.get("correct"))
        feedback = obj.get("feedback") or ("Correct!" if correct else "Not quite -- try again.")
        return [({"kind": "graded", "correct": correct, "feedback": feedback, "given": given}, "out")]

    return answer_checker


role = AgentRoleEntry(
    name="answer_checker",
    in_ports=("in_",),
    out_ports=("out",),
    factory=lambda: Role(fn=make_answer_checker(), statuses=["out"]),
)
