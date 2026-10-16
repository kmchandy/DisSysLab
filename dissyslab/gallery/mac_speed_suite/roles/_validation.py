# dissyslab/gallery/mac_speed_suite/roles/_validation.py
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
