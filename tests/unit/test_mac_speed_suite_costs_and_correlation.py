# tests/unit/test_mac_speed_suite_costs_and_correlation.py
"""
Regression tests for transaction costs (D1) and the strategy correlation
matrix (D2), Phase 1.

D1: the backtester charges a cost on every change of position, so a
high-turnover rule no longer looks free (the 0%-cost fantasy an outside
tester flagged). Costs are net into per_ticker_returns, so every downstream
metric is net-of-cost.

D2: the evaluator emits a correlation matrix across the variants' portfolio
return series -- the "are these secretly the same bet?" view -- and the
report shades it.
"""

from __future__ import annotations

from dissyslab.gallery.apps.mac_speed_suite.roles._backtester_core import (
    DEFAULT_COST_BPS,
    make_backtester,
)
from dissyslab.gallery.apps.mac_speed_suite.roles.evaluator import (
    _correlation_matrix,
    _pearson,
    make_evaluator,
)


def _bt(speed: str, series: dict, cost_bps: float) -> dict:
    out = make_backtester(speed, cost_bps=cost_bps)(
        {"ticker_volatility": {}, "series": series}
    )
    return out[0][0][speed]


# ── D1: transaction costs ─────────────────────────────────────────────


def test_default_cost_is_the_suggested_five_bps():
    assert DEFAULT_COST_BPS == 5.0


def test_entry_incurs_exactly_one_transaction_cost():
    """An always-long position pays one entry cost (flat -> long) on the
    first tradeable day and nothing thereafter, since the position never
    changes again."""
    d = _bt("s", {"A": {"returns": [None, 0.10, 0.10],
                        "signals": {"s": [1.0, 1.0, 1.0]}}}, 10.0)
    r = d["per_ticker_returns"]["A"]
    assert r[0] == 0.0
    assert abs(r[1] - 0.099) < 1e-12   # 0.10 gross - 10bps entry
    assert abs(r[2] - 0.10) < 1e-12    # no position change -> no cost


def test_flat_strategy_pays_no_cost_even_at_a_huge_rate():
    d = _bt("s", {"A": {"returns": [None, 0.05, 0.05],
                        "signals": {"s": [0.0, 0.0, 0.0]}}}, 100.0)
    assert d["per_ticker_returns"]["A"] == [0.0, 0.0, 0.0]


def test_higher_turnover_costs_more():
    """Same zero gross returns; a flipping rule pays more in costs than a
    buy-and-hold rule, so it nets less."""
    flip = {"A": {"returns": [None, 0.0, 0.0, 0.0], "signals": {"s": [1.0, -1.0, 1.0, -1.0]}}}
    hold = {"A": {"returns": [None, 0.0, 0.0, 0.0], "signals": {"s": [1.0, 1.0, 1.0, 1.0]}}}
    net_flip = sum(_bt("s", flip, 10.0)["per_ticker_returns"]["A"])
    net_hold = sum(_bt("s", hold, 10.0)["per_ticker_returns"]["A"])
    assert net_flip < net_hold


def test_cost_bps_is_forwarded_for_the_report():
    out = make_backtester("s", cost_bps=7.0)(
        {"ticker_volatility": {}, "series": {"A": {"returns": [None, 0.01],
                                                   "signals": {"s": [1.0, 1.0]}}}}
    )
    assert out[0][0]["s"]["cost_bps"] == 7.0


# ── D2: correlation ───────────────────────────────────────────────────


def test_pearson_identical_and_negated_series():
    x = [0.01, -0.02, 0.03, -0.01]
    assert abs(_pearson(x, x) - 1.0) < 1e-12
    assert abs(_pearson(x, [-v for v in x]) + 1.0) < 1e-12


def test_pearson_flat_series_is_none_not_a_crash():
    assert _pearson([0.0, 0.0, 0.0], [0.01, 0.02, 0.03]) is None


def test_correlation_matrix_is_symmetric_with_unit_diagonal():
    spr = {"a": [0.01, -0.02, 0.03, -0.01], "b": [0.02, -0.01, 0.01, 0.0]}
    cm = _correlation_matrix(spr)
    assert cm["variants"] == ["a", "b"]
    m = cm["matrix"]
    assert abs(m["a"]["a"] - 1.0) < 1e-12 and abs(m["b"]["b"] - 1.0) < 1e-12
    assert abs(m["a"]["b"] - m["b"]["a"]) < 1e-12


def test_evaluator_output_carries_correlation_and_cost():
    merged = {
        "type": "mac_backtest", "ticker_volatility": {"A": 0.2},
        "x": {"per_ticker_returns": {"A": [0.0, 0.01, -0.01, 0.02]},
              "per_ticker_days_in_market": {"A": 3}, "per_ticker_turnover": {"A": 2.0},
              "cost_bps": 5.0},
        "y": {"per_ticker_returns": {"A": [0.0, -0.01, 0.01, -0.02]},
              "per_ticker_days_in_market": {"A": 3}, "per_ticker_turnover": {"A": 2.0},
              "cost_bps": 5.0},
    }
    out = make_evaluator()(merged)[0][0]
    assert out["cost_bps"] == 5.0
    assert set(out["correlation"]["variants"]) == {"x", "y"}
    # x and y are exact negatives, so their portfolio series are anti-correlated
    r = out["correlation"]["matrix"]["x"]["y"]
    assert r is not None and r < 0


def test_evaluator_handles_unequal_length_tickers_without_crashing():
    """The bug 10-year data exposed: PLTR (a later IPO) has a shorter series
    than the rest, and the positional portfolio combine raised IndexError.
    The evaluator must align by date instead."""
    merged = {
        "type": "mac_backtest", "ticker_volatility": {"A": 0.2, "B": 0.2},
        "s": {
            "per_ticker_returns": {"A": [0.0, 0.01, -0.01], "B": [0.0, 0.02]},
            "per_ticker_dates": {"A": ["d0", "d1", "d2"], "B": ["d1", "d2"]},
            "per_ticker_days_in_market": {"A": 2, "B": 1},
            "per_ticker_turnover": {"A": 2.0, "B": 1.0},
            "cost_bps": 5.0,
        },
    }
    out = make_evaluator()(merged)[0][0]          # must not raise
    assert "s" in out["portfolio_stats"]
    assert out["table"]["A"]["s"]["n_days"] == 3   # each ticker over its own history
    assert out["table"]["B"]["s"]["n_days"] == 2
