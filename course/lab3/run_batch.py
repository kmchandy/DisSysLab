"""Run one variant of Part 1 or Part 2 several times, and keep every trace.

    python run_batch.py part1 --variant open   --runs 3
    python run_batch.py part1 --variant hook   --runs 3
    python run_batch.py part2 --variant base   --runs 10
    python run_batch.py part2 --variant honest --runs 10
    python run_batch.py part2 --variant hook   --runs 10
    python run_batch.py part2 --variant budget --runs 10

Runs go to lab3_runs/ at the top of the repository (git ignores it), one
folder per run, each with trace.json. lab3_runs/spend.json adds up what
the runs cost; a run does not start if it could take the total past
--cap (default $40). A batch can be stopped with Ctrl-C and run again: it
carries on after the runs already done.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
import common

SPEND = common.RUNS / "spend.json"


def spent() -> float:
    return json.loads(SPEND.read_text())["total_usd"] if SPEND.exists() else 0.0


def add_spend(usd: float) -> None:
    SPEND.parent.mkdir(parents=True, exist_ok=True)
    SPEND.write_text(json.dumps({"total_usd": round(spent() + usd, 4)}))


def jobs(part: str, runs: int) -> list[tuple[str, list[str] | None]]:
    """(run name, customer messages or None) for each run in the batch."""
    if part == "part1":
        import part1_dealer
        return [(f"r{n:02d}_{s}", msgs) for n in range(1, runs + 1)
                for s, msgs in part1_dealer.sessions().items()]
    return [(f"r{n:02d}", None) for n in range(1, runs + 1)]


async def one(part: str, variant: str, name: str, msgs, args) -> dict:
    run_dir = common.RUNS / part / variant / name
    run_dir.mkdir(parents=True, exist_ok=True)
    if part == "part1":
        import part1_dealer as p
        options = p.build(run_dir, variant, model=args.model, max_budget_usd=args.per_run)
        prompts = msgs
    else:
        import part2_impossible as p
        options = p.build(run_dir, variant, model=args.model, max_budget_usd=args.per_run)
        prompts = [p.prompt_for(variant)]
    started = time.time()
    trace = await common.run_session(prompts, options)
    if part == "part1":
        outcome = p.outcome(run_dir, trace)
    else:
        import check_part2
        common.save_run(run_dir, {}, trace, {})  # the checker reads the trace
        outcome = check_part2.label(run_dir)
    meta = {"part": part, "variant": variant, "run": name, "model": args.model,
            "seconds": round(time.time() - started, 1)}
    common.save_run(run_dir, meta, trace, outcome)
    return {"cost": common.cost_of(trace), **outcome}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("part", choices=["part1", "part2"])
    ap.add_argument("--variant", required=True)
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--model", default=common.DEFAULT_MODEL)
    ap.add_argument("--per-run", type=float, default=None,
                    help="dollar cap for one run (default 0.25 for part 1, 0.50 for part 2)")
    ap.add_argument("--cap", type=float, default=40.0, help="dollar cap for all runs together")
    args = ap.parse_args()
    args.per_run = args.per_run or (0.25 if args.part == "part1" else 0.50)
    if not common.key_is_set():
        print("ANTHROPIC_API_KEY is not set. See README.md, step 2.")
        return 1
    for name, msgs in jobs(args.part, args.runs):
        folder = common.RUNS / args.part / args.variant / name
        if (folder / "trace.json").exists():
            print(f"{name}: done before, skipped")
            continue
        if spent() + args.per_run > args.cap:
            print(f"Stopped: ${spent():.2f} spent so far, and one more run could pass the "
                  f"${args.cap:.0f} cap. Raise --cap to go on.")
            return 1
        try:
            r = asyncio.run(one(args.part, args.variant, name, msgs, args))
        except Exception as exc:  # noqa: BLE001 -- say it, keep the batch's other runs
            print(f"{name}: FAILED: {type(exc).__name__}: {exc}")
            print("Nothing was charged that the SDK reported. Fix it and run the same "
                  "command again; finished runs are kept.")
            return 1
        add_spend(r["cost"])
        shown = {k: v for k, v in r.items() if k in ("verdict", "attack_got_through",
                                                      "denied_by_hook", "below_floor")}
        print(f"{name}: ${r['cost']:.3f}  {shown}   (total ${spent():.2f})")
    print(f"\nDone. Total spent on Lab 3 runs: ${spent():.2f}. "
          f"python summarize.py shows the rates.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
