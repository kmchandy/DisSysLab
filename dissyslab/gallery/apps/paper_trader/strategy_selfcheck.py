"""
strategy_selfcheck.py -- the Tier-3 guardrail: mechanically check a *generated*
strategy before anyone backtests or paper-trades on it.

The whole DisSysLab thesis has three tiers of user power:

  Tier 1  the tested substrate (ledger, invariant, fill timing) -- we test it.
  Tier 2  named dials (universe, stop, sizing)                  -- no test needed.
  Tier 3  a strategy the user asks Cowork to *invent*           -- WE HELP YOU TEST.

This module is the "we help you test" part. A generated strategy is freeform in
its logic but must honour one contract:

    compute_fn(bars, params) -> [signal_per_bar]
    where signal[t] depends only on bars[0..t]   (NO LOOK-AHEAD)

The single most important check is look-ahead: a peeking strategy looks brilliant
in backtest and bleeds money live. It is also *mechanically detectable* -- recompute
the signal on truncated history and confirm the earlier values do not move when
future bars are added. Cowork alone cannot offer this check; it needs a tested
harness to run it in. That is the point of the whole exercise.

Everything here is pure Python (no framework, no data files) so it runs anywhere
and is fully unit-tested. The skill OFFERS these checks on any generated strategy;
it never forces them -- advise, don't block.
"""

from __future__ import annotations

import math
from typing import Any, Callable, Dict, List, Optional

Bars = List[Dict[str, Any]]
ComputeFn = Callable[[Bars, Any], List[float]]


class CheckResult:
    """One check's outcome: name, passed?, a one-line human message, detail dict."""

    __slots__ = ("name", "passed", "message", "detail")

    def __init__(self, name: str, passed: bool, message: str,
                 detail: Optional[Dict[str, Any]] = None):
        self.name = name
        self.passed = passed
        self.message = message
        self.detail = detail or {}

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        flag = "PASS" if self.passed else "FAIL"
        return f"<{flag} {self.name}: {self.message}>"


def _finite(x: Any) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def check_contract(signal: Any, n_bars: int) -> CheckResult:
    """Output is a list of finite numbers, one per bar."""
    if not isinstance(signal, list):
        return CheckResult("contract", False,
                           f"strategy must return a list, got {type(signal).__name__}")
    if len(signal) != n_bars:
        return CheckResult("contract", False,
                           f"returned {len(signal)} signals for {n_bars} bars "
                           "(must be one signal per bar)")
    bad = [i for i, v in enumerate(signal) if not _finite(v)]
    if bad:
        return CheckResult("contract", False,
                           f"{len(bad)} non-finite signal value(s) "
                           f"(e.g. index {bad[0]} = {signal[bad[0]]!r})",
                           {"bad_indices": bad[:20]})
    return CheckResult("contract", True,
                       f"{n_bars} finite signals, one per bar")


def check_determinism(fn: ComputeFn, bars: Bars, params: Any) -> CheckResult:
    """Same inputs -> same signal. Catches hidden randomness or leaked state."""
    a = fn(bars, params)
    b = fn(bars, params)
    if a != b:
        i = next((k for k in range(min(len(a), len(b))) if a[k] != b[k]), None)
        return CheckResult("determinism", False,
                           "two runs on identical input disagreed"
                           + (f" first at index {i}: {a[i]!r} vs {b[i]!r}" if i is not None
                              else " (different length)"))
    return CheckResult("determinism", True, "identical output on repeat runs")


def check_no_lookahead(fn: ComputeFn, bars: Bars, params: Any,
                       tol: float = 1e-9) -> CheckResult:
    """THE important one. Recompute the signal on prefixes of the history and
    confirm each earlier value is unchanged by the bars that come after it.

    A causal strategy (only uses bars[0..t] to decide signal[t]) passes exactly.
    A strategy that peeks at the future -- a full-series z-score, a trailing max
    that includes tomorrow, tomorrow's return -- shifts an earlier value when the
    tail is added, and is caught here.
    """
    n = len(bars)
    full = fn(bars, params)
    if not isinstance(full, list) or len(full) != n:
        return CheckResult("no_lookahead", False,
                           "cannot run look-ahead check: contract check must pass first")
    # Cut near the end (where peeking bites) plus a couple of interior points.
    cuts = sorted({c for c in (n - 1, n - 2, n - 5, n - 10, n - 20,
                               (n * 3) // 4, n // 2) if 1 <= c < n})
    for cut in cuts:
        prefix = fn(bars[:cut], params)
        if not isinstance(prefix, list) or len(prefix) != cut:
            return CheckResult("no_lookahead", False,
                               f"strategy did not honour the contract on a "
                               f"{cut}-bar prefix (returned {type(prefix).__name__} "
                               f"len {len(prefix) if isinstance(prefix, list) else 'n/a'})")
        for i in range(cut):
            if not (_finite(prefix[i]) and _finite(full[i])):
                continue
            if abs(prefix[i] - full[i]) > tol:
                return CheckResult(
                    "no_lookahead", False,
                    f"LOOK-AHEAD: signal[{i}] = {full[i]:.6g} using all {n} bars, "
                    f"but {prefix[i]:.6g} using only the first {cut}. A decision "
                    "changed when future bars were added -- the strategy is peeking.",
                    {"index": i, "cut": cut, "full": full[i], "prefix": prefix[i]})
    return CheckResult("no_lookahead", True,
                       f"point-in-time stable across {len(cuts)} truncations "
                       "(no future information used)")


def run_selfcheck(fn: ComputeFn, bars: Bars, params: Any,
                  known_case: Optional[Callable[[List[float]], Optional[str]]] = None
                  ) -> Dict[str, Any]:
    """Run all domain-agnostic checks on a generated strategy.

    known_case (optional): a bespoke assertion the user/Cowork supplies for THIS
    strategy -- given the full signal, return None if fine or a failure string.
    (E.g. "on this rising series a trend follower should end long.") Offered as an
    add-on, never required.

    Returns {ok, checks:[...], summary}. `ok` is True only if every check passed.
    """
    checks: List[CheckResult] = []
    signal = fn(bars, params)
    c_contract = check_contract(signal, len(bars))
    checks.append(c_contract)
    if c_contract.passed:
        checks.append(check_determinism(fn, bars, params))
        checks.append(check_no_lookahead(fn, bars, params))
        if known_case is not None:
            msg = known_case(signal)
            checks.append(CheckResult("known_case", msg is None,
                                      msg or "matched the expected behaviour"))
    ok = all(c.passed for c in checks)
    n_pass = sum(1 for c in checks if c.passed)
    return {
        "ok": ok,
        "checks": [{"name": c.name, "passed": c.passed,
                    "message": c.message, "detail": c.detail} for c in checks],
        "summary": f"{n_pass}/{len(checks)} checks passed"
                   + ("" if ok else " -- DO NOT trade on this strategy until fixed"),
    }


def format_report(result: Dict[str, Any]) -> str:
    """Human-readable one-screen report for Cowork to show the user."""
    head = ("Strategy self-check: PASSED" if result["ok"]
            else "Strategy self-check: FAILED")
    lines = [head, f"  {result['summary']}", ""]
    for c in result["checks"]:
        mark = "  [ok]  " if c["passed"] else "  [X]   "
        lines.append(f"{mark}{c['name']}: {c['message']}")
    if not result["ok"]:
        lines += ["", "  A failing self-check means the strategy is not safe to trust yet.",
                  "  Fix it (or ask Cowork to) and re-run before backtesting or paper-trading."]
    return "\n".join(lines)
