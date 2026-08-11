# tests/unit/test_mac_speed_suite_no_trades.py
"""
Regression tests for "never traded" visibility (Phase 1, step B).

A strategy that never takes a position produces an all-zero return series
that is mathematically identical to one that traded to a flat P&L. Before
this fix the evaluator could not tell "never entered" from "lost money",
and a never-trading variant was ranked as if it had traded. These tests
lock in the accounting that makes the two distinguishable:

  * BACKTESTER emits per-ticker `days_in_market` and `turnover`.
  * EVALUATOR carries them into each per-stock cell and sums them to the
    portfolio level.
  * ReportHtmlSink renders a zero-days-in-market variant as a distinct
    "no trades" row rather than a flat 0% that reads like a loss.

They run once, in DisSysLab's own suite, alongside the other tier-3
mac_speed_suite invariant tests (backtester_core, evaluator).
"""

from __future__ import annotations

from dissyslab.gallery.apps.mac_speed_suite.roles._backtester_core import make_backtester
from dissyslab.gallery.apps.mac_speed_suite.roles.evaluator import make_evaluator
from dissyslab.gallery.apps.mac_speed_suite.sinks.report_html_sink import ReportHtmlSink


def _backtest(speed_name: str, series: dict) -> dict:
    out = make_backtester(speed_name)({"ticker_volatility": {}, "series": series})
    assert len(out) == 1 and out[0][1] == "out"
    return out[0][0][speed_name]


# ── BACKTESTER: trade accounting ──────────────────────────────────────


def test_flat_signal_never_trades():
    """A signal that is 0 every day holds no position: zero days in
    market, zero turnover -- and the return series is all zeros, exactly
    the case that used to be indistinguishable from a real flat result."""
    d = _backtest("s", {"AAPL": {"returns": [None, 0.05, 0.05, 0.05],
                                 "signals": {"s": [0.0, 0.0, 0.0, 0.0]}}})
    assert d["per_ticker_days_in_market"]["AAPL"] == 0
    assert d["per_ticker_turnover"]["AAPL"] == 0.0
    assert d["per_ticker_returns"]["AAPL"] == [0.0, 0.0, 0.0, 0.0]


def test_always_long_counts_days_and_one_entry_of_turnover():
    """An always-long signal holds a position on every tradeable day
    (n-1 of them; day 0 has no prior signal) and turns over exactly once
    -- the initial entry from flat, with no further position changes."""
    d = _backtest("s", {"AAPL": {"returns": [None, 0.01, 0.02, 0.03],
                                 "signals": {"s": [1.0, 1.0, 1.0, 1.0]}}})
    assert d["per_ticker_days_in_market"]["AAPL"] == 3
    assert d["per_ticker_turnover"]["AAPL"] == 1.0


def test_flipping_signal_accumulates_turnover_as_position_change():
    """Turnover is the sum of |position change| over the held-position
    series, starting flat. +1 -> -1 -> +1 is an entry (1) then two full
    reversals (2 + 2) = 5.0, while every day still holds a position."""
    d = _backtest("s", {"AAPL": {"returns": [None, 0.0, 0.0, 0.0],
                                 "signals": {"s": [1.0, -1.0, 1.0, -1.0]}}})
    assert d["per_ticker_days_in_market"]["AAPL"] == 3
    assert d["per_ticker_turnover"]["AAPL"] == 5.0


# ── EVALUATOR: carries trade activity to the table and the portfolio ──


def _merged_two_variants() -> dict:
    return {
        "type": "mac_backtest",
        "ticker_volatility": {"AAPL": 0.2},
        "trade": {
            "per_ticker_returns": {"AAPL": [0.0, 0.01, -0.01]},
            "per_ticker_days_in_market": {"AAPL": 2},
            "per_ticker_turnover": {"AAPL": 3.0},
        },
        "flat": {
            "per_ticker_returns": {"AAPL": [0.0, 0.0, 0.0]},
            "per_ticker_days_in_market": {"AAPL": 0},
            "per_ticker_turnover": {"AAPL": 0.0},
        },
    }


def test_evaluator_carries_trade_activity_to_each_cell():
    out = make_evaluator()(_merged_two_variants())[0][0]
    cell_trade = out["table"]["AAPL"]["trade"]
    cell_flat = out["table"]["AAPL"]["flat"]
    assert cell_trade["days_in_market"] == 2
    assert cell_trade["turnover"] == 3.0
    assert cell_trade["n_days"] == 3
    assert cell_flat["days_in_market"] == 0
    assert cell_flat["turnover"] == 0.0


def test_evaluator_sums_trade_activity_to_the_portfolio_level():
    out = make_evaluator()(_merged_two_variants())[0][0]
    assert out["portfolio_stats"]["trade"]["days_in_market"] == 2
    assert out["portfolio_stats"]["trade"]["turnover"] == 3.0
    # The whole point: a variant that never entered on any ticker reads as
    # zero at the portfolio level, so the report can mark it "no trades".
    assert out["portfolio_stats"]["flat"]["days_in_market"] == 0
    assert out["portfolio_stats"]["flat"]["turnover"] == 0.0


# ── REPORT: never-entered renders as a distinct "no trades" row ────────


def _eval_message_for_report() -> dict:
    def stats(dim, turn, sr):
        return {
            "annualized_return": 0.0 if sr is None else 0.1,
            "annualized_volatility": 0.0 if sr is None else 0.1,
            "sharpe_ratio": sr,
            "max_drawdown": 0.0 if sr is None else -0.05,
            "calmar_ratio": None if sr is None else 2.0,
            "sortino_ratio": None if sr is None else 1.2,
            "days_in_market": dim, "turnover": turn, "n_days": 3,
        }
    return {
        "type": "mac_evaluation", "rank_by": "sharpe_ratio", "n_days": 3,
        "table": {"AAPL": {"trade": stats(2, 3.0, 1.0), "flat": stats(0, 0.0, None)}},
        "portfolio_stats": {"trade": stats(2, 3.0, 1.0), "flat": stats(0, 0.0, None)},
        "ranked": ["trade", "flat"],
    }


def test_report_renders_no_trades_as_a_distinct_row(tmp_path):
    out = tmp_path / "report.html"
    ReportHtmlSink(path=str(out)).run(_eval_message_for_report())
    h = out.read_text(encoding="utf-8")
    # never-entered variant is visibly marked and styled, not a flat 0%
    assert "(no trades)" in h
    assert 'class="no-trades"' in h
    # the trading variant still shows real exposure and turnover
    assert "2 / 3" in h
    assert "<th>Turnover</th>" in h
