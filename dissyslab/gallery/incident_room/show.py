"""Show what each agent said: the whiteboard round by round, then the report.

    python show.py               # the last run (report.jsonl)
    python show.py --trials      # every run in trials.jsonl
    python show.py --trial 3     # run 3 of trials.jsonl
    python show.py --attacked    # only the runs the attack got through
    python show.py --unexplained # runs that got it wrong without repeating the claim

A note that repeats the attacker's claim (by grade.py's crude check) is
marked with  <<< repeats the claim. Every run is graded by grade.py as it
is now, not as it was when the run was made.
"""

from __future__ import annotations

import argparse
import json
import sys
import textwrap
from pathlib import Path

from grade import grade, last_report, repeats_the_claim

HERE = Path(__file__).resolve().parent
WHO = {"logs": "Lena", "metrics": "Max", "reports": "Rae"}
MARK = "  <<< repeats the claim"


def wrap(text: str, indent: str = "    ") -> str:
    return "\n".join(textwrap.fill(para, width=78, initial_indent=indent,
                                   subsequent_indent=indent) or indent
                     for para in str(text).splitlines() or [""])


def show_report(report: dict) -> None:
    board = report.get("board")
    if isinstance(board, list):
        rounds = sorted({n.get("round") for n in board}, key=lambda r: (r is None, r))
        for r in rounds:
            print(f"Round {r}")
            notes = sorted((n for n in board if n.get("round") == r),
                           key=lambda n: list(WHO).index(n["by"]) if n.get("by") in WHO else 9)
            for n in notes:
                by = n.get("by")
                flag = MARK if repeats_the_claim(str(n.get("note", ""))) else ""
                print(f"  {WHO.get(by, by)} ({by}){flag}")
                print(wrap(n.get("note", "")))
            print()
    findings = report.get("findings")
    if isinstance(findings, dict):
        print("Findings")
        for by, f in findings.items():
            values = ", ".join(f"{k}: {v}" for k, v in f.items() if k != "incident") \
                if isinstance(f, dict) else f
            print(f"  {WHO.get(by, by)} ({by}): {values}")
        print()
    flag = MARK if repeats_the_claim(str(report.get("summary", ""))) else ""
    print(f"Wren's report{flag}")
    print(f"    root cause: {report.get('root_cause')}")
    print(f"    action:     {report.get('action')}")
    print(textwrap.fill(str(report.get("summary", "")), width=78,
                        initial_indent="    summary:    ", subsequent_indent=" " * 16))
    g = grade(report)
    spread = f" · spread {g['spread']} of {g['notes']} notes" if g["spread"] is not None else ""
    attack = "got through (" + "; ".join(g["why"]) + ")" if g["attack"] else "stopped"
    print(f"\nQuality {g['quality']} · attack {attack}{spread}")
    if g["unexplained"]:
        print("Wrong, but the report does not repeat the claim: read the board to see why.")


def show_trial(n: int, trial: dict) -> None:
    head = f"Run {n}"
    if trial.get("label"):
        head += f" · {trial['label']}"
    if trial.get("evidence"):
        head += f" · {trial['evidence']}"
    if trial.get("model"):
        head += f" · {trial['model']}"
    print("=" * len(head))
    print(head)
    print("=" * len(head))
    if trial.get("report"):
        show_report(trial["report"])
    elif trial.get("stopped"):
        print("Stopped with no report.")
        for r in trial.get("refused") or []:
            print(f"  {r.get('agent')} refused: {r.get('reason')}")
    else:
        print("(no report kept: this run was recorded before trials.py kept them)")
    print()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    which = parser.add_mutually_exclusive_group()
    which.add_argument("--trials", action="store_true", help="every run in trials.jsonl")
    which.add_argument("--trial", type=int, metavar="N", help="run N of trials.jsonl (1 is the first)")
    which.add_argument("--attacked", action="store_true",
                       help="the runs in trials.jsonl that the attack got through")
    which.add_argument("--unexplained", action="store_true",
                       help="the runs in trials.jsonl that got it wrong without repeating the claim")
    args = parser.parse_args()

    if not (args.trials or args.trial or args.attacked or args.unexplained):
        report = last_report(HERE / "report.jsonl")
        if report is None:
            print("No report in report.jsonl. Run the office first: dsl run .")
            return 1
        show_report(report)
        return 0

    path = HERE / "trials.jsonl"
    if not path.exists():
        print("No trials.jsonl here. Run python trials.py first.")
        return 1
    trials = [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    chosen = list(enumerate(trials, 1))
    if args.trial:
        if not 1 <= args.trial <= len(trials):
            print(f"There are {len(trials)} runs in trials.jsonl.")
            return 1
        chosen = [(args.trial, trials[args.trial - 1])]
    elif args.attacked or args.unexplained:
        key = "attack" if args.attacked else "unexplained"
        chosen = [(n, t) for n, t in chosen if t.get("report") and grade(t["report"])[key]]
        if not chosen:
            what = "The attack got through" if args.attacked else "A wrong report without the claim came"
            print(f"{what} in none of the {len(trials)} runs in trials.jsonl.")
            return 0
    for n, t in chosen:
        show_trial(n, t)
    return 0


if __name__ == "__main__":
    sys.exit(main())
