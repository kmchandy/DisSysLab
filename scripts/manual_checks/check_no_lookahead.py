"""
Mechanical, LLM-free correctness checks for a mac_speed_suite strategy's
compute_variant_signal function -- the analog of adaptive_tutor's
check_problem_ground_truth.py for the backtesting domain.

Six checks, in two tiers, plus one convenience wrapper. None of them
require guessing what a bug might look like in someone's new code --
each one tests the strategy's own actual input/output behavior directly.

Tier 1 -- invariants, checkable purely from a function's own
input/output behavior, no human judgment required about THIS
particular strategy:

1. check_no_lookahead -- signal[t] must be a pure function of
   bars[0..t] only (the original, most important check: a strategy
   that peeks at tomorrow's price backtests as implausibly good and
   nobody notices until it matters).
2. check_deterministic -- calling compute_fn twice on identical
   bars/params must produce identical output. Catches hidden
   randomness, wall-clock reads, or accidental global mutable state --
   any of which silently breaks session replay/reproducibility.
3. check_finite -- every returned value must be a finite float. Catches
   a classic bug source (RSI-style average-loss-of-zero division, a
   moving average read before its window has filled) that no-lookahead
   and determinism can't see.
4. check_signal_range -- if the strategy declares itself "directional"
   (must return only -1.0/0.0/1.0) or "sizing" (must stay within a
   declared [min, max]), every value must actually satisfy that. Before
   this check existed, this was just something Step 6 of the skill told
   the LLM to eyeball -- now it's an assertion, not a suggestion.
5. check_warmup -- if a strategy declares it needs `min_bars_required`
   days of history before it can produce a real signal, every day
   before that must equal a declared placeholder value (e.g. 0.0), not
   a crash or garbage/NaN.

Tier 2 -- the honest limitation of everything above: none of these five
checks can catch a strategy that is consistently, deterministically
computing the *wrong thing* (a sign error, the wrong window, price where
you meant volume). They all still pass for a confidently wrong
implementation. The only thing that can catch that class of bug is:

6. assert_matches_golden_example -- a tiny, hand-computed example where
   a human works out the expected signal by hand (using "nice" parameter
   values chosen specifically to make hand arithmetic easy, not the
   strategy's real production variants) and the function is asserted to
   reproduce those exact numbers. This is the backtesting analog of
   adaptive_tutor's honest limitation that its own ground-truth checker
   "deliberately does NOT re-derive whether the arithmetic itself is
   correct" -- here, the golden example is what fills that gap, because
   nothing mechanical can.

`assert_strategy_contract` runs whichever of 1-6 apply (skipping any
whose optional arguments are omitted) in one call -- the backtesting
analog of adaptive_tutor's `assert_subject_contract`.
"""

import math
from typing import Any, Callable, List, Optional, Sequence, Tuple


# ── 1. No lookahead (unchanged from the original version of this file) ──

def check_no_lookahead(
    compute_fn: Callable[[List[dict], Any], List[float]],
    params: Any,
    bars: List[dict],
    sample_every: int = 1,
) -> dict:
    """
    The property being checked, precisely: signal[t] must be a pure
    function of bars[0..t] only. If that's true, then computing the
    signal on the FULL bar history and computing it on a history
    truncated right after day t must agree on day t's value.

    Args:
        compute_fn: a strategy's compute_variant_signal(bars, params) function.
        params: the params value to pass through to compute_fn.
        bars: real (or realistic) daily bar dicts to test against.
        sample_every: check every Nth day rather than every single day.

    Returns a dict:
        {"passed": bool, "n_checked": int, "n_total_days": int,
         "first_violation": {...} or None}
    """
    full_signal = compute_fn(bars, params)
    if len(full_signal) != len(bars):
        raise ValueError(
            f"compute_fn returned {len(full_signal)} signal values for "
            f"{len(bars)} input bars -- these must be the same length, "
            f"one signal value per day."
        )

    n = len(bars)
    first_violation = None
    n_checked = 0

    for t in range(0, n, sample_every):
        truncated_bars = bars[: t + 1]
        truncated_signal = compute_fn(truncated_bars, params)
        n_checked += 1
        if truncated_signal[-1] != full_signal[t]:
            first_violation = {
                "day": t,
                "date": bars[t].get("date"),
                "full_signal_value": full_signal[t],
                "truncated_signal_value": truncated_signal[-1],
            }
            break

    return {
        "passed": first_violation is None,
        "n_checked": n_checked,
        "n_total_days": n,
        "first_violation": first_violation,
    }


def assert_no_lookahead(compute_fn, params, bars, sample_every: int = 1) -> None:
    result = check_no_lookahead(compute_fn, params, bars, sample_every=sample_every)
    if not result["passed"]:
        v = result["first_violation"]
        raise AssertionError(
            f"Lookahead detected at day {v['day']} ({v['date']}): "
            f"signal computed on the full history was {v['full_signal_value']!r}, "
            f"but recomputing with every day after {v['date']} removed gave "
            f"{v['truncated_signal_value']!r}. These must match -- a strategy's "
            f"signal on day t is only allowed to depend on bars[0..t]. Checked "
            f"{result['n_checked']} of {result['n_total_days']} days before "
            f"finding this."
        )


# ── 2. Determinism ───────────────────────────────────────────────────

def check_deterministic(compute_fn, params, bars) -> dict:
    """Same bars, same params, called twice -- must return identical
    output. A strategy relying on wall-clock time, a global RNG, or
    accidental shared mutable state can still pass check_no_lookahead
    (it's checking a different property) while failing this."""
    first = compute_fn(bars, params)
    second = compute_fn(bars, params)
    return {"passed": first == second, "first_run": first, "second_run": second}


def assert_deterministic(compute_fn, params, bars) -> None:
    result = check_deterministic(compute_fn, params, bars)
    if not result["passed"]:
        raise AssertionError(
            "compute_fn is not deterministic: calling it twice on the same "
            "bars and params produced different signals. Check for a call "
            "to wall-clock time, a global random module, or mutable state "
            "shared across calls instead of being recomputed from bars each "
            "time."
        )


# ── 3. Finite values only ────────────────────────────────────────────

def check_finite(compute_fn, params, bars) -> dict:
    """Every returned signal value must be a finite float -- no NaN, no
    +/-inf. Catches division-by-zero-style bugs (e.g. an average-loss
    of zero in an RSI-style calculation) that no-lookahead can't see,
    since a NaN can still be a pure function of bars[0..t]."""
    signal = compute_fn(bars, params)
    for t, value in enumerate(signal):
        if not math.isfinite(value):
            return {
                "passed": False,
                "first_violation": {"day": t, "date": bars[t].get("date"), "value": value},
            }
    return {"passed": True, "first_violation": None}


def assert_finite(compute_fn, params, bars) -> None:
    result = check_finite(compute_fn, params, bars)
    if not result["passed"]:
        v = result["first_violation"]
        raise AssertionError(
            f"Non-finite signal value at day {v['day']} ({v['date']}): "
            f"{v['value']!r}. Every signal value must be a finite float -- "
            f"check for a division by zero or an unfilled lookback window."
        )


# ── 4. Declared signal type/range, actually enforced ────────────────

def check_signal_range(
    compute_fn,
    params,
    bars,
    signal_type: str,
    signal_range: Optional[Tuple[float, float]] = None,
    tol: float = 1e-9,
) -> dict:
    """
    signal_type: "directional" -- every value must be one of
        {-1.0, 0.0, 1.0} (0.0 allowed for a strategy that can be flat,
        e.g. before its first breakout).
    signal_type: "sizing" -- every value must fall within the declared
        `signal_range` (min, max), e.g. (-1.0, 1.0).

    This used to be something Step 6 of the skill told the LLM to
    eyeball ("a plain direction strategy should be -1/0/1..."). It's an
    assertion now, not a suggestion.
    """
    signal = compute_fn(bars, params)
    if signal_type == "directional":
        allowed = {-1.0, 0.0, 1.0}
        for t, value in enumerate(signal):
            if value not in allowed:
                return {
                    "passed": False,
                    "first_violation": {
                        "day": t, "date": bars[t].get("date"), "value": value,
                        "reason": f"directional signal must be one of {sorted(allowed)}",
                    },
                }
    elif signal_type == "sizing":
        if signal_range is None:
            raise ValueError('signal_type="sizing" requires a signal_range=(min, max)')
        lo, hi = signal_range
        for t, value in enumerate(signal):
            if value < lo - tol or value > hi + tol:
                return {
                    "passed": False,
                    "first_violation": {
                        "day": t, "date": bars[t].get("date"), "value": value,
                        "reason": f"outside declared range [{lo}, {hi}]",
                    },
                }
    else:
        raise ValueError(f'signal_type must be "directional" or "sizing", got {signal_type!r}')
    return {"passed": True, "first_violation": None}


def assert_signal_range(compute_fn, params, bars, signal_type, signal_range=None) -> None:
    result = check_signal_range(compute_fn, params, bars, signal_type, signal_range)
    if not result["passed"]:
        v = result["first_violation"]
        raise AssertionError(
            f"Signal value at day {v['day']} ({v['date']}) violates its own "
            f"declared contract: {v['value']!r} -- {v['reason']}."
        )


# ── 5. Warm-up period ────────────────────────────────────────────────

def check_warmup(
    compute_fn, params, bars, min_bars_required: int, warmup_value: float = 0.0, tol: float = 1e-9,
) -> dict:
    """Every day before `min_bars_required` must equal `warmup_value`
    (a well-defined placeholder), not a crash, NaN, or an early guess
    dressed up as a real signal. Not every strategy has a warm-up
    period (e.g. MAC's EWMA is seeded immediately) -- only call this
    check for strategies that declare one."""
    signal = compute_fn(bars, params)
    for t in range(min(min_bars_required, len(signal))):
        if abs(signal[t] - warmup_value) > tol:
            return {
                "passed": False,
                "first_violation": {
                    "day": t, "date": bars[t].get("date"), "value": signal[t],
                    "expected_warmup_value": warmup_value,
                },
            }
    return {"passed": True, "first_violation": None}


def assert_warmup(compute_fn, params, bars, min_bars_required, warmup_value: float = 0.0) -> None:
    result = check_warmup(compute_fn, params, bars, min_bars_required, warmup_value)
    if not result["passed"]:
        v = result["first_violation"]
        raise AssertionError(
            f"Day {v['day']} ({v['date']}) is before this strategy's declared "
            f"min_bars_required={min_bars_required}, so it should equal the "
            f"warm-up placeholder {v['expected_warmup_value']!r}, but got "
            f"{v['value']!r} instead."
        )


# ── 6. Golden example (the one check that catches "confidently wrong") ──

def assert_matches_golden_example(
    compute_fn,
    params,
    golden_bars: List[dict],
    expected_signal: Sequence[float],
    tol: float = 1e-9,
) -> None:
    """
    `golden_bars`/`expected_signal`: a small, hand-computed example --
    pick parameter values that make the arithmetic easy to do by hand
    (e.g. spans that make the EWMA smoothing constant a round number),
    not the strategy's real production variants. This is the one check
    in this file that can catch a strategy that is deterministic,
    finite, in-range, and causally correct, but simply computing the
    wrong formula -- nothing else here can, by construction (see this
    module's docstring).
    """
    actual = compute_fn(golden_bars, params)
    if len(actual) != len(expected_signal):
        raise AssertionError(
            f"Golden example length mismatch: got {len(actual)} signal values, "
            f"expected {len(expected_signal)}."
        )
    for t, (a, e) in enumerate(zip(actual, expected_signal)):
        if abs(a - e) > tol:
            raise AssertionError(
                f"Golden example mismatch at day {t} ({golden_bars[t].get('date')}): "
                f"got {a!r}, expected {e!r}. This means the compute function's "
                f"formula itself is wrong -- not a lookahead, determinism, range, "
                f"or warm-up issue, all of which this specific example was built "
                f"to isolate away from."
            )


# ── Convenience: run every applicable check in one call ─────────────

def assert_strategy_contract(
    compute_fn,
    params,
    bars,
    *,
    signal_type: Optional[str] = None,
    signal_range: Optional[Tuple[float, float]] = None,
    min_bars_required: Optional[int] = None,
    warmup_value: float = 0.0,
    golden_bars: Optional[List[dict]] = None,
    golden_expected: Optional[Sequence[float]] = None,
    sample_every: int = 1,
) -> None:
    """Runs check_no_lookahead, check_deterministic, and check_finite
    unconditionally (every strategy must satisfy these three); runs
    check_signal_range if `signal_type` is given; runs check_warmup if
    `min_bars_required` is given; runs the golden-example check if both
    `golden_bars` and `golden_expected` are given. Raises on the first
    failure, same convention as assert_subject_contract in
    check_problem_ground_truth.py."""
    assert_no_lookahead(compute_fn, params, bars, sample_every=sample_every)
    assert_deterministic(compute_fn, params, bars)
    assert_finite(compute_fn, params, bars)
    if signal_type is not None:
        assert_signal_range(compute_fn, params, bars, signal_type, signal_range)
    if min_bars_required is not None:
        assert_warmup(compute_fn, params, bars, min_bars_required, warmup_value)
    if golden_bars is not None and golden_expected is not None:
        assert_matches_golden_example(compute_fn, params, golden_bars, golden_expected)


def _bar(date: str, price: float) -> dict:
    """Minimal bar dict for a golden example where only `close` (and,
    for Donchian-style strategies, high/low set equal to close) matters
    -- not a full realistic OHLCV bar, deliberately, so the golden
    example's arithmetic stays simple to verify by hand."""
    return {"date": date, "open": price, "high": price, "low": price,
            "close": price, "volume": 0}


if __name__ == "__main__":
    # Self-test: run every check against the office's own three existing
    # strategies (expected to pass -- they were hand-verified for these
    # properties when built) plus one hand-computed golden example each
    # for MAC and Donchian. If any of these fail, the checker itself
    # likely has a bug, not the strategies.
    import os
    import sys

    REPO_ROOT = os.environ.get("DISSYSLAB_ROOT", ".")
    ROLES_DIR = os.path.join(REPO_ROOT, "dissyslab/gallery/apps/mac_speed_suite/roles")
    SP100_DATA = os.path.join(REPO_ROOT, "sp100_data")
    sys.path.insert(0, ROLES_DIR)
    sys.path.insert(0, REPO_ROOT)

    from dissyslab.components.sources.csv_stock_history_source import CSVStockHistorySource
    from mac_signal import MAC_VARIANTS, _mac_compute_variant_signal
    from donchian_signal import DONCHIAN_VARIANTS, _donchian_compute_variant_signal
    from turtle_signal import TURTLE_VARIANTS, _turtle_compute_variant_signal

    src = CSVStockHistorySource(tickers=["AMD", "NFLX", "NVDA", "PLTR", "TSLA"], directory=SP100_DATA)
    history_msg = next(src.run())
    bars = history_msg["history"]["AMD"]

    # (name, fn, params, signal_type, signal_range, min_bars_required, warmup_value)
    checks = [
        ("mac_fast", _mac_compute_variant_signal, MAC_VARIANTS["fast"], "directional", None, None, 0.0),
        ("donchian_20", _donchian_compute_variant_signal, DONCHIAN_VARIANTS["20"], "directional", None, 20, 0.0),
        ("turtle_s1", _turtle_compute_variant_signal, TURTLE_VARIANTS["s1"], "sizing", (-1.0, 1.0), 20, 0.0),
    ]

    all_passed = True
    for name, fn, params, signal_type, signal_range, min_bars, warmup in checks:
        try:
            assert_strategy_contract(
                fn, params, bars,
                signal_type=signal_type, signal_range=signal_range,
                min_bars_required=min_bars, warmup_value=warmup,
            )
            print(f"PASS: {name} (no-lookahead + deterministic + finite + range"
                  f"{' + warmup' if min_bars else ''})")
        except AssertionError as exc:
            all_passed = False
            print(f"FAIL: {name}: {exc}")

    # Golden examples -- deliberately NOT the real production variants;
    # (fast_span=1, slow_span=3) makes both EWMA smoothing constants
    # round numbers (alpha=1.0 and alpha=0.5) so the expected output can
    # be hand-computed exactly. See this module's docstring, tier 2.
    mac_golden_bars = [_bar(f"2025-01-0{i+1}", p) for i, p in enumerate([10, 20, 10, 20, 10, 10, 10, 10])]
    mac_golden_expected = [-1.0, 1.0, -1.0, 1.0, -1.0, -1.0, -1.0, -1.0]
    try:
        assert_matches_golden_example(_mac_compute_variant_signal, (1, 3), mac_golden_bars, mac_golden_expected)
        print("PASS: mac_signal golden example (fast_span=1, slow_span=3)")
    except AssertionError as exc:
        all_passed = False
        print(f"FAIL: mac_signal golden example: {exc}")

    # Donchian golden example, window=2, flat-range bars (high=low=close)
    # so prior_high/prior_low reduce to plain max/min of two closes.
    donchian_golden_bars = [_bar(f"2025-01-0{i+1}", p) for i, p in enumerate([10, 10, 15, 10, 5, 5, 5, 12])]
    donchian_golden_expected = [0.0, 0.0, 1.0, 1.0, -1.0, -1.0, -1.0, 1.0]
    try:
        assert_matches_golden_example(_donchian_compute_variant_signal, 2, donchian_golden_bars, donchian_golden_expected)
        print("PASS: donchian_signal golden example (window=2)")
    except AssertionError as exc:
        all_passed = False
        print(f"FAIL: donchian_signal golden example: {exc}")

    print()
    print("ALL CHECKS PASSED" if all_passed else "SOME CHECKS FAILED")
    sys.exit(0 if all_passed else 1)
