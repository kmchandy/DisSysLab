# dissyslab/gallery/apps/adaptive_tutor/sinks/tutor_session_display.py

"""
TutorSessionDisplay -- console renderer for adaptive_tutor's
``tutor_session_report`` messages, replacing the raw
``{'kind': 'tutor_session_report', ...}`` dict console_printer would
otherwise print.

Why this lives here
--------------------

Same convention as ``debate/sinks/debate_display.py`` and
``periodic_brief/sinks/*``: this display hardcodes adaptive_tutor's own
report shape (``subject``, ``variant``, ``score``, ``results``), so
that knowledge belongs to this app, not to the framework's generic
``components/sinks/``.

What it does
------------

For each session report (one per subject, per run), prints a bordered
header with the subject name, difficulty variant, and score, then one
line per problem with a colored checkmark/cross and the tutor's
feedback -- readable at a glance, unlike the raw dict.
"""

from typing import Any, Dict

GREEN = "\033[92m"
RED = "\033[91m"
GREY = "\033[90m"
BOLD = "\033[1m"
CYAN = "\033[96m"
RESET = "\033[0m"

WIDTH = 60


def _title(subject: str) -> str:
    return subject.replace("_", " ").title()


class TutorSessionDisplay:
    """Sink that renders one adaptive_tutor session report to the terminal."""

    def run(self, msg: Any) -> None:
        if not isinstance(msg, dict) or msg.get("kind") != "tutor_session_report":
            return

        subject = _title(str(msg.get("subject", "?")))
        variant = str(msg.get("variant", "?"))
        score = str(msg.get("score", "?/?"))
        results = msg.get("results") or []

        bar = "─" * WIDTH
        print()
        print(f"{BOLD}{CYAN}┌{bar}┐{RESET}")
        header = f"  {subject} -- {variant} session complete"
        print(f"{BOLD}{CYAN}│{RESET}{BOLD}{header:<{WIDTH}}{RESET}{BOLD}{CYAN}│{RESET}")
        score_line = f"  Score: {score}"
        print(f"{BOLD}{CYAN}│{RESET}{score_line:<{WIDTH}}{BOLD}{CYAN}│{RESET}")
        print(f"{BOLD}{CYAN}├{bar}┤{RESET}")

        for i, r in enumerate(results, start=1):
            correct = bool(r.get("correct"))
            mark = f"{GREEN}✓{RESET}" if correct else f"{RED}✗{RESET}"
            text = str(r.get("text", ""))
            given = str(r.get("given", ""))
            feedback = str(r.get("feedback", ""))
            print(f"{BOLD}{CYAN}│{RESET}  {i}. {mark}  {text}")
            print(f"{BOLD}{CYAN}│{RESET}     {GREY}answer: {RESET}{given}")
            print(f"{BOLD}{CYAN}│{RESET}     {GREY}{feedback}{RESET}")

        print(f"{BOLD}{CYAN}└{bar}┘{RESET}")
