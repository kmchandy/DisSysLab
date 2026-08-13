# tests/unit/test_mac_speed_suite_trades.py
"""
Regression tests for trade-level metrics (Phase 2, E) and R multiples (G).

The trader's reframe: the table measured a daily return series; a trader judges
*trades*. These lock in trade reconstruction (round trips from the position
series), the per-variant trade statistics, and the R multiple = trade return /
stop distance (a disclosed stop, shown alongside -- never imposed).
"""

from __future__ import annotations

from dissyslab.gallery.apps.mac_speed_suite.roles._backtester_core import (
    _reconstruct_trades,
)
from dissyslab.gallery.apps.mac_speed_suite.roles.evaluator import (
    _aggregate_trades,
    _trade_stats,
)


# ── trade reconstruction ──────────────────────────────────────────────


def test_reconstruct_splits_long_and_short_round_trips():
    dates = ["d0", "d1", "d2", "d3", "d4", "d5", "d6", "d7"]
    signal = [0, 1, 1, 0, -1, -1, 0, 1]
    strat = [0.0, 0.10, 0.05, 0.0, 0.02, -0.03, 0.0, 0.04]
    trades = _reconstruct_trades(signal, strat, dates)
    assert len(trades) == 2
    lo, sh = trades
    assert lo["direction"] == "long" and lo["hold"] == 2
    assert lo["entry"] == "d1" and lo["exit"] == "d3"
    assert abs(lo["return"] - 0.05) < 1e-9
    assert sh["direction"] == "short" and abs(sh["return"] + 0.03) < 1e-9
    assert not lo["open"] and not sh["open"]


def test_reconstruct_flags_open_trade_at_window_end():
    trades = _reconstruct_trades([0, 1, 1, 1], [0.0, 0.1, 0.1, 0.1],
                                 ["a", "b", "c", "d"])
    assert len(trades) == 1 and trades[0]["open"] is True


def test_reconstruct_never_in_market_has_no_trades():
    assert _reconstruct_trades([0, 0, 0], [0.0, 0.0, 0.0], ["a", "b", "c"]) == []


# ── trade statistics + R ──────────────────────────────────────────────


def test_trade_stats_counts_wins_and_expectancy():
    trades = [
        {"return": 0.10, "hold": 3, "open": False},
        {"return": -0.04, "hold": 2, "open": False},
        {"return": 0.02, "hold": 1, "open": True},   # open -> excluded from stats
    ]
    st = _trade_stats(trades, stop_pct=None)
    assert st["n_trades"] == 2 and st["n_open"] == 1
    assert abs(st["win_rate"] - 0.5) < 1e-9
    assert abs(st["avg_win"] - 0.10) < 1e-9 and abs(st["avg_loss"] + 0.04) < 1e-9
    assert abs(st["expectancy"] - 0.03) < 1e-9
    assert abs(st["rr"] - 2.5) < 1e-9
    assert "total_r" not in st            # no stop -> no R


def test_trade_stats_r_multiples_use_the_disclosed_stop():
    trades = [{"return": 0.25, "hold": 5, "open": False},   # +2.5R at a 10% stop
              {"return": -0.10, "hold": 2, "open": False}]  # -1.0R
    st = _trade_stats(trades, stop_pct=0.10)
    assert st["stop_pct"] == 0.10
    assert abs(st["total_r"] - 1.5) < 1e-9        # 2.5 + (-1.0)
    assert abs(st["expectancy_r"] - 0.75) < 1e-9
    assert abs(st["avg_win_r"] - 2.5) < 1e-9 and abs(st["avg_loss_r"] + 1.0) < 1e-9


def test_zero_trade_variant_is_explicit_not_a_flat_zero():
    st = _trade_stats([], stop_pct=0.10)
    assert st == {"n_trades": 0, "n_open": 0}


def test_aggregate_pools_trades_across_tickers():
    speed_results = {
        "x": {"per_ticker_trades": {
            "AAA": [{"return": 0.1, "hold": 2, "open": False}],
            "BBB": [{"return": -0.05, "hold": 1, "open": False}],
        }},
        "flat": {"per_ticker_trades": {"AAA": [], "BBB": []}},
    }
    stats, lists = _aggregate_trades(speed_results, stop_pct=0.10)
    assert stats["x"]["n_trades"] == 2
    assert stats["flat"]["n_trades"] == 0
    assert len(lists["x"]) == 2 and all("ticker" in t for t in lists["x"])
