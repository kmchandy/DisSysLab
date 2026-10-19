"""Run the incident room many times and count: a model is not a script.

    python trials.py              # 10 runs
    python trials.py --runs 20

Each run is `dsl run . --quiet`, then grade.py's checks on its report. The
results go to trials.jsonl (one line per run, added to what is there), and
a summary is printed: how often the office found the cause, how often the
attack got through, and how far it spread on the whiteboard.

Which evidence file is used is decided by office.md, as for a single run.
Label the runs so that the table in your write-up can tell them apart:

    python trials.py --label "open board, attacked"

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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--runs", type=int, default=10)
    parser.add_argument("--label", default="")
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
        results.append(g)
        with open(HERE / "trials.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(g) + "\n")
        mark = "stopped" if g["stopped"] else f"quality {g['quality']}, attack {g['attack']}"
        print(f"run {n:>2}: {mark}")

    k = len(results)
    stopped = sum(r["stopped"] for r in results)
    print(f"\n{args.label or 'these runs'}: {k} runs")
    print(f"  found the cause (quality 1): {sum(r['quality'] for r in results)} of {k}")
    print(f"  attack got through:          {sum(r['attack'] for r in results)} of {k}")
    spreads = [r["spread"] for r in results if r.get("spread") is not None]
    if spreads:
        print(f"  spread, notes per run:       {sum(spreads) / len(spreads):.1f} on average")
    print(f"  stopped with no report:      {stopped} of {k} (read refused.jsonl)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
