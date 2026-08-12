# dissyslab/gallery/apps/mac_speed_suite/roles/_walkforward.py
# Shared helpers + stateful agents for walk-forward out-of-sample validation.
# Underscore prefix so load_roles_dir skips it as a role file (the role
# registrations live in window_gate.py and comparator.py).

"""
Walk-forward (out-of-sample) validation, done as an in-office feedback loop.

Why a loop, and why in the office
=================================

Ranking many strategy variants on one window and bolding the winner is how you
pick the luckiest, not the best. Walk-forward guards against that: rank the
variants on an earlier *train* span, then measure those same variants on a
later *test* span they had no part in choosing, and roll that split forward.

We do it *inside* the office as a feedback loop, on the same pattern as the
debate office (a gate that releases one item at a time, a moderator that either
loops back or finishes). Here:

  * WINDOW_GATE holds the full history and a schedule of labelled spans (one
    full-history span for the detailed report, then train/test spans for each
    walk-forward fold). It releases one span at a time -- a sliced copy of the
    history, tagged with its fold and role -- into the *unchanged* pipeline
    (market_context -> signals -> backtest -> evaluate).
  * COMPARATOR receives each span's evaluation, accumulates it, and either
    signals the gate to release the next span (the feedback edge) or, once the
    whole schedule is done, builds the out-of-sample scorecard and emits it to
    the report.

Because it is one office, it is one `dsl run`, one termination, one
checkpointable computation -- and the same machine generalizes to Monte Carlo
(D4): the gate's "bank" becomes resampled histories instead of time slices.

Everything between the gate and the comparator is untouched; the only added
plumbing is a small ``_wf_tag`` (fold / role / total_spans) the workers forward
so the comparator can label each evaluation.
"""

from __future__ import annotations

import random
from typing import Any, Dict, List, Optional, Tuple

from dissyslab.core import Agent

WALKFORWARD_DEFAULT_FOLDS = 4

# A span is (fold, role, start_date, end_date). `fold` is an int for
# train/test folds, or the string "full" for the whole-history span.
Span = Tuple[Any, str, str, str]


# ── Pure helpers (unit-tested without the runtime) ────────────────────


def _all_dates(history: Dict[str, List[dict]]) -> List[str]:
    """Sorted union of every bar date across tickers."""
    dates = {b["date"] for bars in history.values() for b in bars if b.get("date")}
    return sorted(dates)


def build_schedule(history: Dict[str, List[dict]], n_folds: int) -> List[Span]:
    """Build the span schedule: one full-history span (for the detailed
    report), then, for each of ``n_folds`` folds, an expanding train span and
    the next chunk as its test span.

    The dates are split into ``n_folds + 1`` equal chunks. Fold i trains on
    everything up to the end of chunk i and tests on chunk i+1, so chunk 0 is
    the initial train seed and every later chunk is tested out-of-sample
    exactly once.
    """
    dates = _all_dates(history)
    spans: List[Span] = []
    if len(dates) < 2:
        return spans
    spans.append(("full", "full", dates[0], dates[-1]))

    n = len(dates)
    if n_folds < 1 or n < n_folds + 1:
        return spans  # not enough data to fold; just the full span
    cut = [j * n // (n_folds + 1) for j in range(n_folds + 2)]
    for i in range(n_folds):
        train_end = dates[cut[i + 1] - 1]
        test_lo, test_hi = cut[i + 1], cut[i + 2]
        if test_hi <= test_lo:
            continue
        spans.append((i, "train", dates[0], train_end))
        spans.append((i, "test", dates[test_lo], dates[test_hi - 1]))
    return spans


def slice_history(full_msg: Dict[str, Any], start: str, end: str) -> Dict[str, Any]:
    """A stock_history message restricted to bars in [start, end] (inclusive).
    ISO dates compare lexicographically, so string comparison is correct."""
    history = full_msg.get("history", {}) or {}
    sliced = {
        t: [b for b in bars if start <= b.get("date", "") <= end]
        for t, bars in history.items()
    }
    return {
        "type": full_msg.get("type", "stock_history"),
        "tickers": full_msg.get("tickers", list(sliced.keys())),
        "history": sliced,
        "start": start,
        "end": end,
    }


def _mean(values: List[Optional[float]]) -> Optional[float]:
    nums = [v for v in values if isinstance(v, (int, float))]
    return sum(nums) / len(nums) if nums else None


def aggregate_scorecard(
    train_evals: List[Dict[str, Any]], test_evals: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Per-variant in-sample vs out-of-sample summary across folds.

    For each variant, average its portfolio Sharpe and annualized return over
    the train spans (in-sample) and over the test spans (out-of-sample), then
    rank by out-of-sample Sharpe -- the number a trader should actually trust.
    """
    variants: Dict[str, None] = {}
    for e in train_evals + test_evals:
        for v in (e.get("portfolio_stats", {}) or {}):
            variants.setdefault(v, None)

    def avg(evals, variant, key):
        return _mean([e.get("portfolio_stats", {}).get(variant, {}).get(key)
                      for e in evals])

    per_variant: Dict[str, Dict[str, Optional[float]]] = {}
    for v in variants:
        per_variant[v] = {
            "is_sharpe":  avg(train_evals, v, "sharpe_ratio"),
            "oos_sharpe": avg(test_evals, v, "sharpe_ratio"),
            "is_return":  avg(train_evals, v, "annualized_return"),
            "oos_return": avg(test_evals, v, "annualized_return"),
        }

    def oos_key(v):
        s = per_variant[v]["oos_sharpe"]
        return s if isinstance(s, (int, float)) else float("-inf")

    ranked = sorted(per_variant, key=oos_key, reverse=True)
    return {
        "per_variant": per_variant,
        "ranked_by_oos": ranked,
        "n_folds": len(test_evals),
    }


# ── Monte Carlo: same machine, resampled bank ─────────────────────────


def resample_history(
    full_msg: Dict[str, Any], seed: int, block_size: int = 20
) -> Dict[str, Any]:
    """A block-bootstrap resample of the price history, for Monte Carlo.

    Resamples blocks of consecutive days from the shared date grid -- the SAME
    days for every ticker -- so short-run autocorrelation and the daily
    cross-section (which relative strength depends on) are both preserved. Each
    ticker's daily return and intraday shape (open/high/low relative to close)
    for the chosen source day are replayed onto a synthetic, monotonically
    dated price path. Seeded: a given seed always yields the same resample.
    """
    history = full_msg.get("history", {}) or {}
    all_dates = _all_dates(history)
    n = len(all_dates)
    if n < 2:
        return {"type": full_msg.get("type", "stock_history"),
                "tickers": full_msg.get("tickers", []), "history": dict(history)}

    # Per-ticker shape by source date: (return, open/close, high/close,
    # low/close, volume).
    shapes: Dict[str, Dict[str, Tuple[float, float, float, float, float]]] = {}
    for t, bars in history.items():
        ub = [b for b in bars if b.get("close") is not None]
        if len(ub) < 2:
            continue
        by_date: Dict[str, Tuple[float, float, float, float, float]] = {}
        for i in range(1, len(ub)):
            prev_c, c = ub[i - 1]["close"], ub[i]["close"]
            if not prev_c or not c:
                continue
            by_date[ub[i]["date"]] = (
                c / prev_c - 1.0,
                (ub[i].get("open") or c) / c,
                (ub[i].get("high") or c) / c,
                (ub[i].get("low") or c) / c,
                ub[i].get("volume") or 0,
            )
        if by_date:
            shapes[t] = by_date

    rng = random.Random(seed)
    hi = max(0, n - block_size)
    seq: List[int] = []
    while len(seq) < n:
        start = rng.randint(0, hi)
        seq.extend(range(start, min(start + block_size, n)))
    seq = seq[:n]

    new_history: Dict[str, List[dict]] = {}
    for t, by_date in shapes.items():
        prev_close = 100.0
        bars = []
        for j, si in enumerate(seq):
            shape = by_date.get(all_dates[si])
            if shape is None:      # ticker not trading on that source day
                continue
            ret, o_r, h_r, l_r, vol = shape
            close = prev_close * (1.0 + ret)
            prev_close = close
            bars.append({
                "date": f"S{j:05d}", "open": close * o_r, "high": close * h_r,
                "low": close * l_r, "close": close, "volume": vol,
            })
        if len(bars) >= 2:
            new_history[t] = bars

    return {"type": full_msg.get("type", "stock_history"),
            "tickers": list(new_history.keys()), "history": new_history}


def _percentile(values: List[Optional[float]], q: float) -> Optional[float]:
    nums = sorted(v for v in values if isinstance(v, (int, float)))
    if not nums:
        return None
    idx = min(len(nums) - 1, max(0, int(round(q * (len(nums) - 1)))))
    return nums[idx]


def aggregate_distribution(mc_evals: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Per-variant outcome distribution across the Monte Carlo resamples: the
    median and a 5th-95th band on annualized return, the median Sharpe, a
    worst-case (5th-percentile) drawdown, and the probability of a losing
    outcome. Ranked by median return."""
    variants: Dict[str, None] = {}
    for e in mc_evals:
        for v in (e.get("portfolio_stats", {}) or {}):
            variants.setdefault(v, None)

    def col(v, key):
        return [e.get("portfolio_stats", {}).get(v, {}).get(key) for e in mc_evals]

    per: Dict[str, Dict[str, Optional[float]]] = {}
    for v in variants:
        rets = col(v, "annualized_return")
        nums = [x for x in rets if isinstance(x, (int, float))]
        per[v] = {
            "return_p5":  _percentile(rets, 0.05),
            "return_p50": _percentile(rets, 0.50),
            "return_p95": _percentile(rets, 0.95),
            "sharpe_p50": _percentile(col(v, "sharpe_ratio"), 0.50),
            "drawdown_worst": _percentile(col(v, "max_drawdown"), 0.05),
            "prob_loss": (sum(1 for x in nums if x < 0) / len(nums)) if nums else None,
        }

    def median_return(v):
        m = per[v]["return_p50"]
        return m if isinstance(m, (int, float)) else float("-inf")

    ranked = sorted(per, key=median_return, reverse=True)
    return {"per_variant": per, "ranked_by_median": ranked,
            "n_samples": len(mc_evals)}


# ── Stateful agents (thin run() wrappers over testable step methods) ──


class _WindowGate(Agent):
    """Release one labelled span at a time into the pipeline.

    First inbound message is the full history from the source; every later
    message is a "next" signal from the comparator. Emits the next scheduled
    span on each; when the schedule is exhausted it keeps looping (so
    termination detection can close the office), exactly like the debate gate.
    """

    def __init__(self, n_folds: int = WALKFORWARD_DEFAULT_FOLDS, name=None):
        super().__init__(name=name, inports=["in_"], outports=["out_"])
        self._n_folds = n_folds
        self._full: Optional[Dict[str, Any]] = None
        self._spans: Optional[List[Span]] = None
        self._cursor = 0

    def next_span(self, msg: Any) -> Optional[Dict[str, Any]]:
        """Update state from an inbound message and return the next span to
        send, or None when uninitialized/exhausted. Pure enough to unit-test
        without the runtime."""
        if (self._spans is None and isinstance(msg, dict)
                and msg.get("history")):
            self._full = msg
            self._spans = build_schedule(msg.get("history", {}), self._n_folds)
            self._cursor = 0
        if not self._spans or self._cursor >= len(self._spans):
            return None
        fold, role, start, end = self._spans[self._cursor]
        self._cursor += 1
        span = slice_history(self._full, start, end)
        span["_wf_tag"] = {
            "fold": fold, "role": role, "total_spans": len(self._spans),
        }
        return span

    def run(self) -> None:
        while True:
            msg = self.recv("in_")
            span = self.next_span(msg)
            if span is not None:
                self.send(span, "out_")
            # else: not yet initialized, or schedule exhausted -> keep looping
            # so os_agent can poll us and shut the office down cleanly.


class _MonteCarloGate(Agent):
    """Release a full-history span, then ``n_samples`` seeded block-bootstrap
    resamples of it, one per signal -- the same loop as WINDOW_GATE, but the
    bank is resampled histories instead of time slices. Drop-in replacement:
    same wiring, same comparator (which builds a distribution from the
    ``mc``-tagged spans), same pipeline."""

    def __init__(self, n_samples: int = 200, seed: int = 42,
                 block_size: int = 20, name=None):
        super().__init__(name=name, inports=["in_"], outports=["out_"])
        self._n = n_samples
        self._seed = seed
        self._block = block_size
        self._full: Optional[Dict[str, Any]] = None
        self._cursor = 0

    def next_span(self, msg: Any) -> Optional[Dict[str, Any]]:
        if self._full is None and isinstance(msg, dict) and msg.get("history"):
            self._full = msg
            self._cursor = 0
        if self._full is None:
            return None
        total = 1 + self._n
        if self._cursor >= total:
            return None
        i = self._cursor
        self._cursor += 1
        if i == 0:
            span = dict(self._full)      # full-history span (detailed report)
            span["_wf_tag"] = {"fold": "full", "role": "full", "total_spans": total}
        else:
            span = resample_history(self._full, seed=self._seed + i,
                                    block_size=self._block)
            span["_wf_tag"] = {"fold": i - 1, "role": "mc", "total_spans": total}
        return span

    def run(self) -> None:
        while True:
            msg = self.recv("in_")
            span = self.next_span(msg)
            if span is not None:
                self.send(span, "out_")


class _Comparator(Agent):
    """Accumulate each span's evaluation; loop the gate until the schedule is
    done, then emit the out-of-sample scorecard to the report.

    Outports (semantic -> runtime): "out" -> out_0 (report/console),
    "next" -> out_1 (feedback to the gate).
    """

    def __init__(self, name=None):
        super().__init__(name=name, inports=["in_"], outports=["out_0", "out_1"])
        self._full_eval: Optional[Dict[str, Any]] = None
        self._train: List[Dict[str, Any]] = []
        self._test: List[Dict[str, Any]] = []
        self._mc: List[Dict[str, Any]] = []
        self._count = 0
        self._total: Optional[int] = None

    def accept(self, msg: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
        """Fold one evaluation in; return ("next", signal) to release the next
        span, or ("scorecard", message) once every span has been seen. Pure
        enough to unit-test without the runtime."""
        tag = (msg.get("_wf_tag") or {}) if isinstance(msg, dict) else {}
        role = tag.get("role")
        if tag.get("total_spans") is not None:
            self._total = tag["total_spans"]
        self._count += 1
        if role == "full":
            self._full_eval = msg
        elif role == "train":
            self._train.append(msg)
        elif role == "test":
            self._test.append(msg)
        elif role == "mc":
            self._mc.append(msg)

        if self._total is not None and self._count >= self._total:
            base = dict(self._full_eval or msg)   # renders the detailed report
            if self._train or self._test:
                base["walk_forward"] = aggregate_scorecard(self._train, self._test)
            if self._mc:
                base["monte_carlo"] = aggregate_distribution(self._mc)
            return ("scorecard", base)
        return ("next", {"walkforward_next": True})

    def run(self) -> None:
        while True:
            msg = self.recv("in_")
            kind, out = self.accept(msg)
            if kind == "scorecard":
                self.send(out, "out_0")      # semantic "out" -> report + console
            else:
                self.send(out, "out_1")      # semantic "next" -> gate


# ── One gate that runs BOTH validations in a single office pass ────────


class _ValidationGate(Agent):
    """Release the walk-forward schedule *and then* the Monte Carlo resamples
    into the unchanged pipeline, so one ``dsl run`` produces a report with both
    an out-of-sample scorecard and a robustness distribution -- with no
    office.md editing.

    The schedule is: a full-history span (for the detailed report), then the
    expanding train/test folds (walk-forward), then ``n_samples`` seeded
    block-bootstrap resamples (Monte Carlo). Each span is tagged so the
    unchanged COMPARATOR builds ``walk_forward`` from the train/test spans and
    ``monte_carlo`` from the ``mc`` spans off the same ``total_spans`` count.

    Flags let a caller -- or Cowork, in plain English -- shape the run without
    touching code:

      * ``n_samples`` -- how many Monte Carlo resamples (modest by default;
        raise it for a tighter distribution).
      * ``monte_carlo=False`` -- walk-forward only (fast).
      * ``walk_forward=False`` -- Monte Carlo only (still emits one full span
        so the detailed report renders).
    """

    def __init__(self, n_folds: int = WALKFORWARD_DEFAULT_FOLDS,
                 n_samples: int = 100, seed: int = 42, block_size: int = 20,
                 walk_forward: bool = True, monte_carlo: bool = True,
                 name=None):
        super().__init__(name=name, inports=["in_"], outports=["out_"])
        self._n_folds = n_folds
        self._n = n_samples
        self._seed = seed
        self._block = block_size
        self._walk_forward = walk_forward
        self._monte_carlo = monte_carlo
        self._full: Optional[Dict[str, Any]] = None
        self._plan: Optional[List[Tuple]] = None
        self._cursor = 0

    def _build_plan(self, history: Dict[str, List[dict]]) -> List[Tuple]:
        """Ordered list of span descriptors: ("wf", fold, role, start, end) or
        ("mc", i). Always includes exactly one full-history span."""
        plan: List[Tuple] = []
        if self._walk_forward:
            for (fold, role, start, end) in build_schedule(history, self._n_folds):
                plan.append(("wf", fold, role, start, end))
        if not any(d[0] == "wf" and d[2] == "full" for d in plan):
            all_d = _all_dates(history)
            if len(all_d) >= 2:
                plan.append(("wf", "full", "full", all_d[0], all_d[-1]))
        if self._monte_carlo:
            for i in range(self._n):
                plan.append(("mc", i))
        return plan

    def next_span(self, msg: Any) -> Optional[Dict[str, Any]]:
        if (self._plan is None and isinstance(msg, dict) and msg.get("history")):
            self._full = msg
            self._plan = self._build_plan(msg.get("history", {}))
            self._cursor = 0
        if not self._plan or self._cursor >= len(self._plan):
            return None
        desc = self._plan[self._cursor]
        self._cursor += 1
        total = len(self._plan)
        if desc[0] == "wf":
            _, fold, role, start, end = desc
            span = slice_history(self._full, start, end)
            span["_wf_tag"] = {"fold": fold, "role": role, "total_spans": total}
        else:  # ("mc", i)
            i = desc[1]
            span = resample_history(self._full, seed=self._seed + i + 1,
                                    block_size=self._block)
            span["_wf_tag"] = {"fold": i, "role": "mc", "total_spans": total}
        return span

    def run(self) -> None:
        while True:
            msg = self.recv("in_")
            span = self.next_span(msg)
            if span is not None:
                self.send(span, "out_")
            # else: not yet initialized, or plan exhausted -> keep looping so
            # os_agent can shut the office down cleanly.
