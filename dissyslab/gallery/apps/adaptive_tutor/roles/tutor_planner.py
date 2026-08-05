# dissyslab/gallery/apps/adaptive_tutor/roles/tutor_planner.py

"""
PLANNER -- shared session orchestrator. Like mac_speed_suite's
BACKTESTER/EVALUATOR, this role never changes per subject: it only
ever sees problems as opaque dicts with text/correct_answer/
accepted_forms/grading_notes, all supplied by whichever subject's BANK
it's wired to (see ``_subject_common.py``). Adding a new subject never
touches this file.

``subject_name`` is a label only (for the final report), forwarded
via kwarg the same way ``backtester(speed_name=...)`` is in
mac_speed_suite -- confirmed static roles can take office.md kwargs
this way (see mac_speed_suite/roles/backtester.py's docstring).

Message flow (one session, sequential -- no multi-student concurrency
in this v1; see office README for that as a follow-on, matching
tutor_multi.py's later generalization of the single-student office
this replaces):

    START ─start(variant)─▶ PLANNER ─start_session─▶ BANK
                                │  ◀───session_bank──────┘
                                ├─ask(index)──▶ STUDENT ─answer(index)─▶ PLANNER
                                ├─grade(...)──▶ CHECKER ─graded────────▶ PLANNER
                                └─report (session done)──▶ console_printer

Input kinds on the single "in_" (BANK/STUDENT/CHECKER all fan into it;
the compiler auto-inserts a MergeAsynch, same pattern
recovery_demo/roles/pi_combiner.py uses -- see that file for the
precedent):
    {"kind": "start", "variant": "easy"}
    {"kind": "session_bank", "subject": ..., "variant": ..., "problems": [...]}
    {"kind": "answer", "index": <int>, "given": <str>}
    {"kind": "graded", "correct": <bool>, "feedback": <str>}
"""

from typing import Any, Dict

from dissyslab.blocks.role import Role
from dissyslab.office.library import AgentRoleEntry


def make_tutor_planner(subject_name: str):
    session: Dict[str, Any] = {"variant": None, "problems": [], "index": 0, "results": []}

    def planner(msg: Dict[str, Any]):
        kind = msg.get("kind")

        if kind == "start":
            session["variant"] = msg.get("variant", "easy")
            return [({"kind": "start_session", "variant": session["variant"]}, "to_bank")]

        if kind == "session_bank":
            session["problems"] = msg["problems"]
            session["index"] = 0
            session["results"] = []
            return _ask_current(session)

        if kind == "answer":
            idx = msg["index"]
            problem = session["problems"][idx]
            return [({
                "kind": "grade",
                "text": problem["text"],
                "correct_answer": problem["correct_answer"],
                "accepted_forms": problem["accepted_forms"],
                "grading_notes": problem.get("grading_notes", ""),
                "given": msg["given"],
            }, "to_checker")]

        if kind == "graded":
            session["results"].append({
                "text": session["problems"][session["index"]]["text"],
                "given": msg.get("given", ""),
                "correct": msg["correct"],
                "feedback": msg["feedback"],
            })
            session["index"] += 1
            if session["index"] < len(session["problems"]):
                return _ask_current(session)
            return [(_final_report(subject_name, session), "report")]

        return []

    return planner


def _ask_current(session: Dict[str, Any]):
    idx = session["index"]
    problem = session["problems"][idx]
    return [({
        "kind": "ask", "index": idx, "text": problem["text"],
        "correct_answer": problem["correct_answer"],
        "accepted_forms": problem["accepted_forms"],
        "distractor": problem.get("distractor", ""),
    }, "to_student")]


def _final_report(subject_name: str, session: Dict[str, Any]) -> Dict[str, Any]:
    n_correct = sum(1 for r in session["results"] if r["correct"])
    return {
        "kind": "tutor_session_report",
        "subject": subject_name,
        "variant": session["variant"],
        "score": f"{n_correct}/{len(session['results'])}",
        "results": session["results"],
    }


role = AgentRoleEntry(
    name="tutor_planner",
    in_ports=("in_",),
    out_ports=("to_bank", "to_student", "to_checker", "report"),
    factory=lambda subject_name: Role(
        fn=make_tutor_planner(subject_name), statuses=["to_bank", "to_student", "to_checker", "report"],
    ),
)
