# tests/unit/test_mac_speed_suite_relative_strength.py
"""
Regression tests for relative strength (Phase 1, step C).

A per-ticker compute function only ever sees one ticker's bars, so it cannot
express "strong relative to the market / peers". Step C adds a MARKET_CONTEXT
stage that computes cross-sectional strength causally, plus an *optional*
context argument on the signal wrapper so a strategy can opt in -- without
changing any existing strategy or the shared machinery downstream.

These lock in the three things that make that safe and correct:
  * _accepts_context / make_signal_computer: existing two-arg strategies are
    called unchanged; a three-arg strategy is handed per-ticker context.
  * MARKET_CONTEXT ranks are correct and causal (past values do not change
    when future data is truncated -- the property the no-lookahead check
    depends on).
  * rs_trend goes long only when the stock's own trend is up AND it is strong
    vs peers, and stays flat (no lookahead) otherwise.
"""

from __future__ import annotations

from dissyslab.gallery.apps.mac_speed_suite.roles._signal_common import (
    _accepts_context,
    make_signal_computer,
)
from dissyslab.gallery.apps.mac_speed_suite.roles.market_context import (
    make_market_context,
)
from dissyslab.gallery.apps.mac_speed_suite.roles.rs_trend import (
    _rs_trend_compute_variant_signal,
)


def _bars(closes):
    return [
        {"date": f"d{i}", "open": c, "high": c, "low": c, "close": c, "volume": 0}
        for i, c in enumerate(closes)
    ]


def _hist(closes_by_ticker):
    return {
        "type": "stock_history",
        "tickers": list(closes_by_ticker),
        "history": {t: _bars(cl) for t, cl in closes_by_ticker.items()},
    }


# ── opt-in detection ──────────────────────────────────────────────────


def test_accepts_context_distinguishes_two_arg_from_context_aware():
    assert _accepts_context(lambda bars, params: None) is False
    assert _accepts_context(lambda bars, params, context=None: None) is True

    def kwonly(bars, params, *, context=None):
        return None

    assert _accepts_context(kwonly) is True


# ── backward compatibility: two-arg strategies are untouched ──────────


def test_two_arg_strategy_output_identical_with_or_without_context():
    """An existing (bars, params) strategy must produce byte-identical
    signals whether or not the message carries a context field -- the
    guarantee that MARKET_CONTEXT is transparent to every current
    strategy."""
    def two_arg(bars, params):
        return [float(params)] * len(bars)

    fn = make_signal_computer("x", {"v": 7}, two_arg)
    msg = {"history": {"A": _bars([10, 11, 12])}}
    with_ctx = dict(msg)
    with_ctx["context"] = {
        "per_ticker": {"A": {"rs_percentile_by_date": {"d0": 0.9}}},
        "market_return_by_date": {"d1": 0.05},
        "n_tickers": 3,
        "lookback": 63,
    }
    assert fn(msg)[0][0]["series"] == fn(with_ctx)[0][0]["series"]


def test_context_is_reshaped_per_ticker_and_aligned_by_date():
    """An opted-in (bars, params, context) strategy receives this ticker's
    context as positional arrays aligned to its bars by date."""
    seen = {}

    def three_arg(bars, params, context=None):
        seen["ctx"] = context
        return [0.0] * len(bars)

    fn = make_signal_computer("y", {"v": 1}, three_arg)
    msg = {
        "history": {"A": _bars([10, 11])},
        "context": {
            "per_ticker": {
                "A": {
                    "rs_percentile_by_date": {"d0": 0.3, "d1": 0.7},
                    "rs_rank_by_date": {"d0": 2, "d1": 1},
                    "rel_strength_by_date": {"d1": 0.02},
                }
            },
            "market_return_by_date": {"d1": 0.05},
            "n_tickers": 3,
            "lookback": 63,
        },
    }
    fn(msg)
    assert seen["ctx"]["rs_percentile"] == [0.3, 0.7]      # aligned to d0, d1
    assert seen["ctx"]["rs_rank"] == [2, 1]
    assert seen["ctx"]["market_returns"] == [None, 0.05]
    assert seen["ctx"]["n_tickers"] == 3


# ── MARKET_CONTEXT: correct ranking, and causal ───────────────────────


def test_market_context_ranks_by_momentum_strongest_first():
    """At a date where A rose most and C least over the lookback, A must
    rank 1 (strongest) and C last."""
    hist = _hist({"A": [10, 10, 10, 20],   # momentum over 2 days = +100%
                  "B": [10, 10, 10, 15],   # +50%
                  "C": [10, 10, 10, 11]})  # +10%
    ctx = make_market_context(lookback=2)(hist)[0][0]["context"]
    ranks = {t: ctx["per_ticker"][t]["rs_rank_by_date"]["d3"] for t in "ABC"}
    assert ranks == {"A": 1, "B": 2, "C": 3}


def test_market_context_is_causal_under_truncation():
    """A ticker's rank on a past date must not change when later data is
    removed -- the property the whole no-lookahead guarantee rests on."""
    closes = {"A": [10, 10, 12, 9, 20], "B": [10, 10, 11, 13, 8], "C": [10, 10, 10, 10, 10]}
    full = make_market_context(lookback=2)(_hist(closes))[0][0]["context"]
    trunc = make_market_context(lookback=2)(
        _hist({t: c[:3] for t, c in closes.items()})
    )[0][0]["context"]
    for t in "ABC":
        for d, rank in trunc["per_ticker"][t]["rs_rank_by_date"].items():
            assert full["per_ticker"][t]["rs_rank_by_date"][d] == rank


# ── rs_trend: long only when trending AND strong ──────────────────────


def test_rs_trend_long_only_when_trend_up_and_strong():
    bars = _bars([10, 11, 12, 13, 14])          # steadily rising -> trend up
    params = {"trend_lb": 2, "min_percentile": 0.5}
    # strong on days 2 and 4, weak on day 3
    context = {"rs_percentile": [None, None, 0.9, 0.2, 0.9]}
    sig = _rs_trend_compute_variant_signal(bars, params, context)
    # trend_up holds for t>=2; long only where percentile >= 0.5
    assert sig == [0.0, 0.0, 1.0, 0.0, 1.0]


def test_rs_trend_stays_flat_without_context():
    """No MARKET_CONTEXT upstream -> no relative-strength signal -> flat.
    (Never trades, rather than silently trading on missing information.)"""
    bars = _bars([10, 11, 12, 13, 14])
    params = {"trend_lb": 2, "min_percentile": 0.5}
    assert _rs_trend_compute_variant_signal(bars, params, None) == [0.0] * 5
