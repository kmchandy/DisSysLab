# tests/unit/test_mac_speed_suite_evaluator.py
"""
Tier-3 invariant tests for EVALUATOR (`evaluator.py`) -- shared,
strategy-agnostic statistics and portfolio-construction machinery every
mac_speed_suite strategy relies on unchanged. Runs once, in DisSysLab's
own permanent test suite, rather than being re-verified per new
strategy (contrast with check_no_lookahead.py, which does run per new
strategy, because it's checking something genuinely strategy-specific).

These lock in the formulas documented in evaluator.py's own docstring
(annualization by sqrt(252)/^(252/n), sample std with an n-1
denominator, downside-only Sortino, inverse-volatility portfolio
weights summing to 1) so a future edit to this shared file can't
silently change what every strategy's numbers mean, without a test
failing -- exactly the guarantee the "shared machinery never changes
per strategy" contract depends on actually holding.
"""

from __future__ import annotations

import math

from dissyslab.gallery.apps.mac_speed_suite.roles.evaluator import (
    _equal_blend,
    _inverse_volatility_weights,
    _scale_to_target_volatility,
    _weighted_portfolio_returns,
    annualized_return,
    annualized_volatility,
    calmar_ratio,
    compute_stats,
    max_drawdown,
    sharpe_ratio,
    sortino_ratio,
)

TRADING_DAYS_PER_YEAR = 252.0


# ── Per-series statistics: edge cases exact enough to hand-verify ──────

def test_flat_zero_returns_are_all_well_defined_edge_cases():
    """A perfectly flat (all-zero) return series: no gain, no
    volatility, and every ratio that divides by volatility/drawdown
    must come back None (not a ZeroDivisionError, not a made-up 0)."""
    stats = compute_stats([0.0, 0.0, 0.0, 0.0])
    assert stats["annualized_return"] == 0.0
    assert stats["annualized_volatility"] == 0.0
    assert stats["sharpe_ratio"] is None
    assert stats["max_drawdown"] == 0.0
    assert stats["calmar_ratio"] is None
    assert stats["sortino_ratio"] is None


def test_total_wipeout_is_exactly_minus_100_percent_annualized():
    """A single -100% day: wealth goes to exactly 0, so the documented
    formula wealth**(252/n) - 1 gives exactly -1.0 regardless of n --
    a hand-verifiable exact edge case, not an approximation."""
    assert annualized_return([-1.0]) == -1.0
    assert max_drawdown([-1.0]) == -1.0
    assert calmar_ratio(-1.0, -1.0) == -1.0


def test_monotonically_positive_series_has_zero_drawdown_and_no_calmar():
    """A return series that only ever goes up never dips below its own
    running peak -- max_drawdown must be exactly 0.0, and calmar_ratio
    (which divides by drawdown size) must come back None, not inf."""
    returns = [0.01, 0.02, 0.01, 0.03]
    assert max_drawdown(returns) == 0.0
    ann_ret = annualized_return(returns)
    assert calmar_ratio(ann_ret, 0.0) is None


def test_no_downside_days_gives_none_sortino_not_a_crash():
    """Sortino only penalizes returns below target (default 0%). A
    series with no day below 0 has zero downside deviation -- must
    come back None, exactly like sharpe_ratio does when volatility is
    zero, not a division by zero."""
    ann_ret = annualized_return([0.01, 0.02])
    assert sortino_ratio([0.01, 0.02], ann_ret) is None


def test_annualized_volatility_matches_documented_sample_std_formula():
    """Recomputed independently via the exact formula the docstring
    claims (sample standard deviation, n-1 denominator, scaled by
    sqrt(252)) -- a regression lock on the formula itself, since a
    silent switch to a population (n) denominator would change every
    strategy's numbers without any test noticing otherwise."""
    returns = [0.01, -0.02, 0.015, -0.005]
    n = len(returns)
    mean = sum(returns) / n
    expected_variance = sum((r - mean) ** 2 for r in returns) / (n - 1)
    expected = (expected_variance ** 0.5) * (TRADING_DAYS_PER_YEAR ** 0.5)
    assert math.isclose(annualized_volatility(returns), expected, rel_tol=1e-12)


def test_sharpe_ratio_is_return_over_volatility():
    assert sharpe_ratio(0.12, 0.06) == 2.0
    assert sharpe_ratio(0.0, 0.0) is None


# ── Portfolio construction ──────────────────────────────────────────────

def test_inverse_volatility_weights_are_proportional_and_sum_to_one():
    """Weight ∝ 1/volatility, normalized to sum to 1 -- hand-computed:
    vol A=0.1 -> inverse 10; vol B=0.2 -> inverse 5; total 15 ->
    weights 10/15 and 5/15."""
    weights = _inverse_volatility_weights({"A": 0.1, "B": 0.2}, ["A", "B"])
    assert math.isclose(weights["A"], 10 / 15, rel_tol=1e-12)
    assert math.isclose(weights["B"], 5 / 15, rel_tol=1e-12)
    assert math.isclose(sum(weights.values()), 1.0, rel_tol=1e-12)


def test_zero_volatility_ticker_excluded_not_division_by_zero():
    """A ticker with unknown/zero volatility must be excluded from the
    portfolio rather than getting an infinite (1/0) weight."""
    weights = _inverse_volatility_weights({"A": 0.1, "B": 0.0}, ["A", "B"])
    assert "B" not in weights
    assert math.isclose(weights["A"], 1.0, rel_tol=1e-12)


def test_all_zero_volatility_falls_back_to_equal_weight():
    """If every ticker lacks volatility info, fall back to equal-weight
    across all of them rather than producing an empty portfolio."""
    weights = _inverse_volatility_weights({"A": 0.0, "B": 0.0}, ["A", "B"])
    assert weights == {"A": 0.5, "B": 0.5}


def test_weighted_portfolio_returns_is_the_weighted_sum_per_day():
    per_ticker = {"A": [0.10, 0.20], "B": [0.00, 0.00]}
    weights = {"A": 0.5, "B": 0.5}
    combined = _weighted_portfolio_returns(per_ticker, weights)
    assert combined == [0.05, 0.10]


def test_scale_to_target_volatility_hits_the_target_exactly():
    """After scaling, the series' own annualized volatility must equal
    the requested target -- otherwise the whole point of comparing
    every speed "on equal footing" silently breaks."""
    returns = [0.01, -0.02, 0.015, -0.005, 0.03, -0.01]
    scaled = _scale_to_target_volatility(returns, target_annual_vol=0.10)
    assert math.isclose(annualized_volatility(scaled), 0.10, rel_tol=1e-9)


def test_scale_to_target_volatility_is_a_noop_on_zero_volatility_series():
    """A flat series has nothing to scale -- must be returned as-is,
    not divide by zero."""
    assert _scale_to_target_volatility([0.0, 0.0], target_annual_vol=0.10) == [0.0, 0.0]


def test_equal_blend_averages_every_speed_day_by_day():
    blend = _equal_blend({"fast": [0.10, 0.20], "slow": [0.00, 0.00]})
    assert blend == [0.05, 0.10]


def test_weighted_portfolio_aligns_by_date_with_unequal_length_tickers():
    """A basket member with a shorter history (e.g. a later IPO) must combine
    by date, not by position: on a date where only some tickers trade, the
    weights are renormalized across those present."""
    per_ticker = {"A": [0.10, 0.20], "B": [0.02, 0.04, 0.06]}
    per_ticker_dates = {"A": ["d1", "d2"], "B": ["d0", "d1", "d2"]}
    weights = {"A": 0.5, "B": 0.5}
    out = _weighted_portfolio_returns(per_ticker, weights, per_ticker_dates)
    # d0: only B present -> renorm to 1.0 -> 0.02
    # d1: A 0.10, B 0.04, equal weights -> 0.07
    # d2: A 0.20, B 0.06 -> 0.13
    assert out == [0.02, 0.07, 0.13]
