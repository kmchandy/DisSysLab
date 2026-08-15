"""
Tests for the Tier-3 strategy self-check. Pure. python3 -m pytest test_strategy_selfcheck.py -q

The critical assertion: the look-ahead check must PASS a causal strategy and
FAIL a peeking one. If that distinction ever breaks, the guardrail is worthless.
"""

from __future__ import annotations

import math

from strategies import mac_crossover
from strategy_selfcheck import (
    check_contract, check_determinism, check_no_lookahead,
    format_report, run_selfcheck,
)


def _series(n=120, start=100.0):
    # A wavy but deterministic price path (no randomness in tests).
    return [{"close": start + 10.0 * math.sin(i / 7.0) + i * 0.3} for i in range(n)]


# ---- causal (honest) strategies pass -----------------------------------------

def test_causal_mac_passes_all_checks():
    bars = _series()
    r = run_selfcheck(mac_crossover, bars, (8, 32))
    assert r["ok"], format_report(r)
    names = {c["name"] for c in r["checks"]}
    assert {"contract", "determinism", "no_lookahead"} <= names


def test_no_lookahead_passes_a_trailing_window_strategy():
    # Momentum vs a trailing average -- causal, must pass.
    def trailing(bars, params):
        w = params
        closes = [b["close"] for b in bars]
        out = []
        for t in range(len(closes)):
            lo = max(0, t - w + 1)
            avg = sum(closes[lo:t + 1]) / (t - lo + 1)
            out.append(1.0 if closes[t] > avg else -1.0)
        return out
    assert check_no_lookahead(trailing, _series(), 10).passed


# ---- peeking (dishonest) strategies are caught -------------------------------

def test_no_lookahead_catches_future_return_peek():
    # Classic cheat: signal[t] uses tomorrow's price. Brilliant backtest, fake.
    def peeker(bars, params):
        closes = [b["close"] for b in bars]
        out = []
        for t in range(len(closes)):
            nxt = closes[t + 1] if t + 1 < len(closes) else closes[t]
            out.append(1.0 if nxt > closes[t] else -1.0)
        return out
    res = check_no_lookahead(peeker, _series(), None)
    assert not res.passed
    assert "LOOK-AHEAD" in res.message
    # And the whole self-check must fail because of it.
    assert not run_selfcheck(peeker, _series(), None)["ok"]


def test_no_lookahead_catches_full_series_zscore():
    # Standardising with the WHOLE series' mean/std is look-ahead too.
    def zscore(bars, params):
        closes = [b["close"] for b in bars]
        mean = sum(closes) / len(closes)
        var = sum((c - mean) ** 2 for c in closes) / len(closes)
        std = math.sqrt(var) or 1.0
        return [1.0 if (c - mean) / std > 0 else -1.0 for c in closes]
    assert not check_no_lookahead(zscore, _series(), None).passed


# ---- contract + determinism ---------------------------------------------------

def test_contract_flags_wrong_length():
    assert not check_contract([1.0, -1.0], 5).passed


def test_contract_flags_nan_and_inf():
    assert not check_contract([1.0, float("nan"), -1.0], 3).passed
    assert not check_contract([1.0, float("inf"), -1.0], 3).passed


def test_contract_rejects_non_list():
    assert not check_contract({"a": 1}, 3).passed


def test_determinism_catches_stateful_strategy():
    state = {"n": 0}
    def drifting(bars, params):
        state["n"] += 1
        return [float(state["n"])] * len(bars)  # output depends on call count
    assert not check_determinism(drifting, _series(10), None).passed


def test_known_case_hook_can_fail_and_pass():
    bars = _series()
    fail = run_selfcheck(mac_crossover, bars, (8, 32),
                         known_case=lambda sig: "expected all longs" )
    assert not fail["ok"]
    ok = run_selfcheck(mac_crossover, bars, (8, 32),
                       known_case=lambda sig: None)
    assert ok["ok"]


def test_format_report_is_readable_both_ways():
    good = run_selfcheck(mac_crossover, _series(), (8, 32))
    assert "PASSED" in format_report(good)
    def peeker(bars, params):
        closes = [b["close"] for b in bars]
        return [1.0 if (closes[t + 1] if t + 1 < len(closes) else closes[t]) > closes[t]
                else -1.0 for t in range(len(closes))]
    bad = run_selfcheck(peeker, _series(), None)
    rep = format_report(bad)
    assert "FAILED" in rep and "no_lookahead" in rep
