"""
Tests for SIZER (risk_sizer) -- the named sizing-policy dispatch -- plus a
signals -> size -> reconcile -> fill -> ledger integration. Pure Python:

    python3 -m pytest test_risk_sizer.py -q
"""

from __future__ import annotations

import pytest

from order_generator import generate_orders
from paper_broker import make_fills
from paper_ledger import replay
from risk_sizer import target_positions

PRICES = {"A": 100.0, "B": 50.0}
VOLS = {"A": 0.2, "B": 0.4}
EQ = 100000.0


# ── the named policies ────────────────────────────────────────────────

def test_inverse_vol_is_the_default_and_weights_by_one_over_vol():
    t = target_positions({"A": 1, "B": 1}, EQ, PRICES, VOLS, {})   # no sizing -> default
    # w_A = (1/0.2)/(1/0.2 + 1/0.4) = 0.6667 ; w_B = 0.3333
    assert t["A"] == pytest.approx(0.6667 * EQ / 100.0, rel=1e-3)
    assert t["B"] == pytest.approx(0.3333 * EQ / 50.0, rel=1e-3)


def test_equal_weight_splits_equity_evenly():
    t = target_positions({"A": 1, "B": 1}, EQ, PRICES, VOLS, {"sizing": "equal_weight"})
    assert t["A"] == pytest.approx(500.0)     # 50k / 100
    assert t["B"] == pytest.approx(1000.0)    # 50k / 50


def test_fixed_fraction_allocates_a_set_fraction_per_name():
    t = target_positions({"A": 1, "B": 1}, EQ, PRICES, VOLS,
                         {"sizing": "fixed_fraction", "fixed_fraction": 0.1})
    assert t["A"] == pytest.approx(100.0) and t["B"] == pytest.approx(200.0)


def test_risk_based_sizes_each_position_to_one_R():
    t = target_positions({"A": 1, "B": 1}, EQ, PRICES, VOLS,
                         {"sizing": "risk_based", "risk_frac": 0.01, "stop_pct": 0.10})
    # notional = 0.01*100000/0.10 = 10000 per name
    assert t["A"] == pytest.approx(100.0) and t["B"] == pytest.approx(200.0)


# ── direction, inactivity, caps ───────────────────────────────────────

def test_short_signal_gives_negative_shares_and_zero_is_flat():
    t = target_positions({"A": -1, "B": 1, "C": 0}, EQ, {"A": 100, "B": 50, "C": 10},
                         VOLS, {"sizing": "equal_weight"})
    assert t["A"] == pytest.approx(-500.0)    # short 50k
    assert t["B"] == pytest.approx(1000.0)
    assert t["C"] == pytest.approx(0.0)       # inactive


def test_max_names_keeps_highest_conviction():
    t = target_positions({"A": 0.5, "B": 1.0, "C": 0.8}, EQ,
                         {"A": 100, "B": 50, "C": 20}, VOLS,
                         {"sizing": "equal_weight", "max_names": 2})
    assert t["A"] == pytest.approx(0.0)       # lowest conviction dropped
    assert t["B"] > 0 and t["C"] > 0


def test_no_leverage_scales_gross_down_to_equity():
    t = target_positions({"A": 1, "B": 1}, EQ, PRICES, VOLS,
                         {"sizing": "fixed_fraction", "fixed_fraction": 0.6})
    gross = abs(t["A"]) * 100.0 + abs(t["B"]) * 50.0
    assert gross == pytest.approx(EQ)         # 2 * 60% scaled back to 100%


def test_inverse_vol_falls_back_to_equal_weight_without_vols():
    t = target_positions({"A": 1, "B": 1}, EQ, PRICES, {}, {})   # no vols
    assert t["A"] == pytest.approx(500.0) and t["B"] == pytest.approx(1000.0)


def test_unknown_sizing_policy_raises():
    with pytest.raises(ValueError):
        target_positions({"A": 1}, EQ, PRICES, VOLS, {"sizing": "bogus"})


def test_zero_equity_is_all_flat():
    t = target_positions({"A": 1, "B": 1}, 0.0, PRICES, VOLS, {})
    assert t == {"A": 0.0, "B": 0.0}


# ── integration: signals -> size -> reconcile -> fill -> ledger ───────

def test_signals_to_book_end_to_end():
    signals = {"A": 1, "B": 1}
    targets = target_positions(signals, EQ, PRICES, VOLS, {"sizing": "equal_weight"})
    orders, _ = generate_orders(targets, {}, PRICES, EQ, {"no_trade_band": 0.005}, "d")
    fills, _ = make_fills(orders, PRICES, {"cost_bps": 0.0})   # cost 0 -> exact fit
    book = replay([{"type": "genesis", "starting_cash": EQ, "initial_positions": {}},
                   {"type": "run", "trade_date": "d", "fills": fills}])
    assert book.positions["A"] == pytest.approx(500.0)
    assert book.positions["B"] == pytest.approx(1000.0)
    assert book.cash == pytest.approx(0.0, abs=1e-6)           # fully invested


def test_inverse_vol_tolerates_none_vols():
    # a ticker with unknown (None) vol must be excluded, not crash
    t = target_positions({"A": 1, "B": 1}, EQ, PRICES, {"A": 0.2, "B": None}, {})
    assert t["A"] > 0 and t["B"] == pytest.approx(0.0)
    # all-None -> equal-weight fallback
    t2 = target_positions({"A": 1, "B": 1}, EQ, PRICES, {"A": None, "B": None}, {})
    assert t2["A"] == pytest.approx(500.0) and t2["B"] == pytest.approx(1000.0)
