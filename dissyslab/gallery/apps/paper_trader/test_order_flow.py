"""
Tests for RECON (order_generator) and FILL (paper_broker), plus an end-to-end
flat->target flow through the ledger. Pure Python:

    python3 -m pytest test_order_flow.py -q
"""

from __future__ import annotations

import pytest

from order_generator import generate_orders
from paper_broker import make_fills
from paper_ledger import Book, _apply_fill, order_id, replay

P = {"AMD": 143.0, "NVDA": 400.0}
POL = {"no_trade_band": 0.005}


# ── RECON: order_generator ────────────────────────────────────────────

def test_entry_from_flat_buys_the_target():
    orders, reasons = generate_orders({"AMD": 70}, {}, P, 100000.0, POL, "2026-08-15")
    assert orders == [{"order_id": order_id("2026-08-15", "AMD", "buy", 70),
                       "ticker": "AMD", "side": "buy", "qty": 70}]
    assert reasons["AMD"]["order"] == {"side": "buy", "qty": 70}


def test_no_trade_band_holds_a_small_delta():
    # equity = 90000 + 70*143 = 100010; band$ = 500.05; 1 share * 143 = 143 < band
    orders, reasons = generate_orders({"AMD": 71}, {"AMD": 70}, P, 90000.0, POL, "d")
    assert orders == []
    assert "within no-trade band" in reasons["AMD"]["reason"]


def test_exit_sells_the_position():
    orders, _ = generate_orders({"AMD": 0}, {"AMD": 50}, P, 0.0, POL, "d")
    assert orders == [{"order_id": order_id("d", "AMD", "sell", 50),
                       "ticker": "AMD", "side": "sell", "qty": 50}]


def test_sells_fund_buys_and_buy_is_trimmed():
    # hold 10 NVDA (sell -> $4000), also want 70 AMD ($10010) with $0 cash
    orders, reasons = generate_orders({"NVDA": 0, "AMD": 70}, {"NVDA": 10},
                                      P, 0.0, POL, "d")
    sells = [o for o in orders if o["side"] == "sell"]
    buys = [o for o in orders if o["side"] == "buy"]
    assert sells[0]["ticker"] == "NVDA" and sells[0]["qty"] == 10
    assert buys[0]["ticker"] == "AMD"
    assert buys[0]["qty"] == pytest.approx(4000.0 / 143.0)     # trimmed to freed cash
    assert "trimmed" in reasons["AMD"]["reason"]


def test_insufficient_cash_trims_the_buy():
    orders, reasons = generate_orders({"AMD": 70}, {}, P, 1000.0, POL, "d")
    assert orders[0]["qty"] == pytest.approx(1000.0 / 143.0)


def test_no_price_produces_no_order():
    orders, reasons = generate_orders({"XYZ": 10}, {}, {}, 100000.0, POL, "d")
    assert orders == [] and "no price" in reasons["XYZ"]["reason"]


# ── FILL: paper_broker ────────────────────────────────────────────────

def test_buy_fill_price_cost_and_cash_delta():
    orders = [{"order_id": "d:AMD:buy:70", "ticker": "AMD", "side": "buy", "qty": 70}]
    fills, skipped = make_fills(orders, {"AMD": 143.0},
                                {"cost_bps": 5.0, "slippage_bps": 0.0})
    f = fills[0]
    assert f["fill_price"] == pytest.approx(143.0)
    assert f["cost"] == pytest.approx(0.0005 * 70 * 143.0)
    assert f["cash_delta"] == pytest.approx(-(70 * 143.0) - 0.0005 * 70 * 143.0)
    assert skipped == []


def test_slippage_moves_buy_up_and_sell_down():
    buy, _ = make_fills([{"order_id": "x", "ticker": "AMD", "side": "buy", "qty": 1}],
                        {"AMD": 100.0}, {"slippage_bps": 10.0})
    sell, _ = make_fills([{"order_id": "y", "ticker": "AMD", "side": "sell", "qty": 1}],
                         {"AMD": 100.0}, {"slippage_bps": 10.0})
    assert buy[0]["fill_price"] == pytest.approx(100.0 * 1.001)
    assert sell[0]["fill_price"] == pytest.approx(100.0 * 0.999)


def test_no_price_is_skipped_not_guessed():
    fills, skipped = make_fills(
        [{"order_id": "x", "ticker": "XYZ", "side": "buy", "qty": 1}], {}, {})
    assert fills == [] and skipped[0]["reason"] == "no open price"


def test_fill_cash_delta_matches_ledger_application():
    fills, _ = make_fills(
        [{"order_id": "x", "ticker": "AMD", "side": "buy", "qty": 70}],
        {"AMD": 143.0}, {"cost_bps": 5.0})
    b = Book(cash=100000.0)
    before = b.cash
    _apply_fill(b, fills[0])
    assert (b.cash - before) == pytest.approx(fills[0]["cash_delta"])


# ── end to end: RECON -> FILL -> ledger ───────────────────────────────

def test_flat_to_target_through_the_ledger():
    targets, prices = {"AMD": 70}, {"AMD": 143.0}
    orders, _ = generate_orders(targets, {}, prices, 100000.0, POL, "2026-08-15")
    fills, _ = make_fills(orders, prices, {"cost_bps": 5.0})
    genesis = {"type": "genesis", "starting_cash": 100000.0, "initial_positions": {}}
    run = {"type": "run", "trade_date": "2026-08-15", "fills": fills}
    book = replay([genesis, run])
    assert book.positions["AMD"] == pytest.approx(70)
    assert book.cost_basis["AMD"] == pytest.approx(143.0)
    assert book.cash == pytest.approx(100000.0 - 70 * 143.0 - 0.0005 * 70 * 143.0)
