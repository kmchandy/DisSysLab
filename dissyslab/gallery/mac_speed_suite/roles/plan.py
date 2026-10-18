"""
---
emits: the spans to validate, one at a time: full, walk-forward folds, Monte Carlo samples
kind: author
out: span, type, tickers, history, _wf_tag
---
Arguments: n_folds, n_samples, seed, block_size, walk_forward, monte_carlo,
stop_pct.

Receives two kinds of message on its one inbox: the price history from
the source (with "type": "stock_history" and "history") and
{"msg_type": "next"} from the comparator, which releases the next span.
The two share no field, so there is no in: line: in: is checked on
every message, and no field is in both. The span logic is unchanged
from version 1 (``_validation.py``).
"""

from _validation import (
    WALKFORWARD_DEFAULT_FOLDS,
    _all_dates,
    build_schedule,
    resample_history,
    slice_history,
)


class Plan:
    def __init__(self, n_folds=WALKFORWARD_DEFAULT_FOLDS, n_samples=100, seed=42,
                 block_size=20, walk_forward=True, monte_carlo=True, stop_pct=0.10):
        self.settings = dict(n_folds=n_folds, n_samples=n_samples, seed=seed,
                             block_size=block_size, walk_forward=walk_forward,
                             monte_carlo=monte_carlo, stop_pct=stop_pct)
        self.state = {"full": None, "plan": None, "cursor": 0, "run_config": None}

    def _build_plan(self, history):
        s = self.settings
        plan = []
        if s["walk_forward"]:
            for (fold, role, start, end) in build_schedule(history, s["n_folds"]):
                plan.append(("wf", fold, role, start, end))
        if not any(d[0] == "wf" and d[2] == "full" for d in plan):
            dates = _all_dates(history)
            if len(dates) >= 2:
                plan.append(("wf", "full", "full", dates[0], dates[-1]))
        if s["monte_carlo"]:
            for i in range(s["n_samples"]):
                plan.append(("mc", i))
        return plan

    def _run_config(self, full):
        s = self.settings
        history = full.get("history", {}) or {}
        dates = _all_dates(history)
        return {
            "tickers": full.get("tickers") or sorted(history.keys()),
            "start": dates[0] if dates else None,
            "end": dates[-1] if dates else None,
            "n_bars": len(dates),
            "walk_forward": s["walk_forward"],
            "monte_carlo": s["monte_carlo"],
            "n_folds": s["n_folds"] if s["walk_forward"] else 0,
            "n_samples": s["n_samples"] if s["monte_carlo"] else 0,
            "block_size": s["block_size"],
            "stop_pct": s["stop_pct"],
        }

    def __call__(self, item):
        st = self.state
        if st["plan"] is None and item.get("history"):
            st["full"] = item
            st["plan"] = self._build_plan(item["history"])
            st["cursor"] = 0
            st["run_config"] = self._run_config(item)
        if not st["plan"] or st["cursor"] >= len(st["plan"]):
            return []
        desc = st["plan"][st["cursor"]]
        st["cursor"] += 1
        total = len(st["plan"])
        if desc[0] == "wf":
            _, fold, role, start, end = desc
            span = slice_history(st["full"], start, end)
            tag = {"fold": fold, "role": role, "total_spans": total}
            if role == "full":
                tag["run_config"] = st["run_config"]
            name = f"{role}_{fold}"
        else:
            i = desc[1]
            span = resample_history(st["full"], seed=self.settings["seed"] + i + 1,
                                    block_size=self.settings["block_size"])
            tag = {"fold": i, "role": "mc", "total_spans": total}
            name = f"mc_{i}"
        span["_wf_tag"] = tag
        span["span"] = name
        return [span]
