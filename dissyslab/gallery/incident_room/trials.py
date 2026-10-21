"""Run the incident room many times and count: a model is not a script.

    python trials.py                                    # 10 runs
    python trials.py --runs 20 --evidence evidence/clean.jsonl

Each run is `dsl run . --quiet`, then grade.py's checks on its report. The
results go to trials.jsonl (one line per run, added to what is there, with
the whole report, so `python show.py --trial N` can show any run), and a
summary is printed: how often the office found the cause, how often the
attack got through, and how far it spread on the whiteboard.

The office reads evidence.jsonl. --evidence copies another file over it
first (one of those in evidence/, or your own), and it stays there
afterwards, so a plain `dsl run .` uses it too. Label the runs so that the
table in your write-up can tell them apart:

    python trials.py --evidence evidence/status_page.jsonl --label "A, status page"

A run that is not this office (Lab 2's Claude track) is any command that
writes report.jsonl here:

    python trials.py --command "python claude_room.py" --label "SDK, attacked"
"""

from __future__ import annotations

import argparse
import json
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

from grade import grade, last_report

HERE = Path(__file__).resolve().parent


def _lines(path: Path) -> list[str]:
    if not path.exists():
        return []
    return [ln for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--runs", type=int, default=10)
    parser.add_argument("--label", default="")
    parser.add_argument("--evidence", default="",
                        help="copy this file to evidence.jsonl first, e.g. evidence/clean.jsonl")
    parser.add_argument("--command", default="",
                        help='what one run is, if not the office here: "python claude_room.py"')
    args = parser.parse_args()
    if args.command:
        command = shlex.split(args.command)
    else:
        dsl = shutil.which("dsl")
        if dsl is None:
            print("dsl is not on your PATH: activate your virtual environment first (setup, step 1).")
            return 1
        command = [dsl, "run", ".", "--quiet"]
    if args.evidence:
        chosen = Path(args.evidence)
        if not chosen.is_absolute():
            chosen = HERE / chosen
        if not chosen.is_file():
            print(f"No evidence file {args.evidence}. The ones that come with the lab are in evidence/.")
            return 1
        if chosen.resolve() != (HERE / "evidence.jsonl").resolve():
            shutil.copyfile(chosen, HERE / "evidence.jsonl")
    evidence = args.evidence or "evidence.jsonl"
    refused_file = HERE / "refused.jsonl"
    results = []
    for n in range(1, args.runs + 1):
        report_file = HERE / "report.jsonl"
        if report_file.exists():
            report_file.unlink()
        done = subprocess.run(command, cwd=HERE,
                              capture_output=True, text=True)
        report = last_report(report_file)
        if report is None:
            # No report at all: the office stopped (a refusal) or failed.
            g = {"quality": 0, "attack": 0, "spread": None, "stopped": True,
                 "exit": done.returncode}
        else:
            g = grade(report) | {"stopped": False, "exit": done.returncode}
        g["label"] = args.label
        g["evidence"] = evidence
        g["report"] = report
        # Each run starts refused.jsonl afresh, so what is there now is this run's.
        g["refused"] = [json.loads(ln) for ln in _lines(refused_file)]
        results.append(g)
        with open(HERE / "trials.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(g) + "\n")
        mark = "stopped" if g["stopped"] else f"quality {g['quality']}, attack {g['attack']}"
        print(f"run {n:>2}: {mark}")

    k = len(results)
    stopped = sum(r["stopped"] for r in results)
    print(f"\n{args.label or 'these runs'}: {k} runs on {evidence}")
    print(f"  found the cause (quality 1): {sum(r['quality'] for r in results)} of {k}")
    print(f"  attack got through:          {sum(r['attack'] for r in results)} of {k}")
    spreads = [r["spread"] for r in results if r.get("spread") is not None]
    if spreads:
        print(f"  spread, notes per run:       {sum(spreads) / len(spreads):.1f} on average")
    print(f"  stopped with no report:      {stopped} of {k} (read refused.jsonl)")
    print("`python show.py --trials` shows what every agent said in each run.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
