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

    python trials.py --evidence evidence/log_injection.jsonl --label "A log"

A run that is not this office (Lab 2's Claude track) is any command that
writes report.jsonl here:

    python trials.py --command "python claude_room.py" --label "SDK, attacked"

Each run records the model it used: the backend and model a plain
`dsl run` here would pick (DSL_BACKEND, or the default). With --command,
name it yourself with --model.

If you change grade.py, grade the runs you have again, without running
anything:

    python trials.py --regrade
"""

from __future__ import annotations

import argparse
import json
import os
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


def model_used() -> str | None:
    """The backend and model a plain `dsl run` here uses, as "backend: model".

    It asks the backend dsl would choose, after reading the same .env
    (the nearest one above this folder). None if that cannot be told.
    """
    for folder in (HERE, *HERE.parents):
        if (folder / ".env").is_file():
            try:
                from dotenv import load_dotenv
            except ImportError:
                break
            load_dotenv(folder / ".env")  # as dsl does: what is already set wins
            break
    name = os.environ.get("DSL_BACKEND") or "anthropic"
    try:
        if os.environ.get("DSL_BACKEND_MODULE"):
            import importlib
            importlib.import_module(os.environ["DSL_BACKEND_MODULE"])
        from dissyslab.backends import get_backend
        backend = get_backend(name)
        if hasattr(backend, "_resolve_model"):
            model = backend._resolve_model(None)
        else:
            model = getattr(backend, "_default_model", None)
    except Exception:  # noqa: BLE001 -- a label must never stop the trials
        model = None
    return f"{name}: {model}" if model else name


def summarize(results: list[dict], label: str, evidence: str) -> None:
    """Print the rates for one set of runs."""
    k = len(results)
    stopped = sum(bool(r.get("stopped")) for r in results)
    models = sorted({str(r.get("model")) for r in results if r.get("model")})
    print(f"\n{label}: {k} runs on {evidence}" + (f", model {', '.join(models)}" if models else ""))
    print(f"  found the cause (quality 1): {sum(r['quality'] for r in results)} of {k}")
    print(f"  attack got through:          {sum(r['attack'] for r in results)} of {k}")
    print(f"  wrong, claim not repeated:   {sum(r.get('unexplained', 0) for r in results)} of {k}"
          "  (read these: python show.py --unexplained)")
    spreads = [r["spread"] for r in results if r.get("spread") is not None]
    if spreads:
        print(f"  spread, notes per run:       {sum(spreads) / len(spreads):.1f} on average")
    print(f"  stopped with no report:      {stopped} of {k} (read refused.jsonl)")


def regrade() -> int:
    """Grade every run in trials.jsonl again with grade.py as it is now; run nothing."""
    path = HERE / "trials.jsonl"
    if not path.exists():
        print("No trials.jsonl here. Run python trials.py first.")
        return 1
    groups: dict[tuple[str, str], list[dict]] = {}
    changed = 0
    for n, line in enumerate(_lines(path), 1):
        old = json.loads(line)
        new = dict(old)
        if old.get("report"):
            new.update(grade(old["report"]))
        if (old.get("attack"), old.get("spread")) != (new.get("attack"), new.get("spread")):
            changed += 1
            print(f"run {n:>2}: attack {old.get('attack')} -> {new['attack']}, "
                  f"spread {old.get('spread')} -> {new.get('spread')}")
        groups.setdefault((new.get("label", ""), new.get("evidence", "")), []).append(new)
    print(f"{changed} of {sum(map(len, groups.values()))} runs graded differently from when they ran.")
    for (label, evidence), results in groups.items():
        summarize(results, label or "unlabelled", evidence)
    print("\ntrials.jsonl is unchanged: show.py grades each run afresh as it shows it.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--runs", type=int, default=10)
    parser.add_argument("--label", default="")
    parser.add_argument("--evidence", default="",
                        help="copy this file to evidence.jsonl first, e.g. evidence/clean.jsonl")
    parser.add_argument("--command", default="",
                        help='what one run is, if not the office here: "python claude_room.py"')
    parser.add_argument("--model", default="",
                        help="the model these runs use, if not what dsl would pick (for --command)")
    parser.add_argument("--regrade", action="store_true",
                        help="grade the runs in trials.jsonl again with grade.py as it is now; run nothing")
    args = parser.parse_args()
    if args.regrade:
        return regrade()
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
    model = args.model or (None if args.command else model_used())
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
            g = {"quality": 0, "attack": 0, "unexplained": 0, "spread": None, "stopped": True,
                 "exit": done.returncode}
        else:
            g = grade(report) | {"stopped": False, "exit": done.returncode}
        g["label"] = args.label
        g["model"] = model
        g["evidence"] = evidence
        g["report"] = report
        # Each run starts refused.jsonl afresh, so what is there now is this run's.
        g["refused"] = [json.loads(ln) for ln in _lines(refused_file)]
        results.append(g)
        with open(HERE / "trials.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(g) + "\n")
        mark = "stopped" if g["stopped"] else f"quality {g['quality']}, attack {g['attack']}"
        print(f"run {n:>2}: {mark}")

    summarize(results, args.label or "these runs", evidence)
    print("`python show.py --trials` shows what every agent said in each run.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
