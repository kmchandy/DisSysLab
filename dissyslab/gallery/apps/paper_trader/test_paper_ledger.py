"""
Tests for the paper_trader book/ledger core. Pure Python, runnable anywhere:

    python3 -m pytest test_paper_ledger.py -q

They pin the book algebra (average-cost basis, realized P&L net of cost),
mark-to-market, deterministic order ids, day-level idempotency, the
snapshot == replay invariant, and append-only correction via compensation.
"""

from __future__ import annotations

import pytest

from paper_ledger import (
    Book,
    apply_event,
    books_equal,
    has_trade_date,
    invariant_holds,
    mark_to_market,
    order_id,
    replay,
)


def genesis(cash=100000.0, positions=None):
    return {"type": "genesis", "starting_cash": cash,
            "initial_positions": positions or {}}


def run(date, fills):
    return {"type": "run", "trade_date": date, "fills": fills}


def fill(ticker, side, qty, price, cost=0.0, date="2026-08-15"):
    return {"order_id": order_id(date, ticker, side, qty), "ticker": ticker,
            "side": side, "qty": qty, "fill_price": price, "cost": cost}


# ── genesis ───────────────────────────────────────────────────────────

def test_genesis_flat_is_all_cash():
    b = replay([genesis(100000.0)])
    assert b.cash == pytest.approx(100000.0)
    assert b.positions == {} and b.realized_pnl == 0.0


def test_genesis_seeds_holdings_with_cost_basis():
    b = replay([genesis(20000.0, {"AMD": {"shares": 100, "cost_basis": 138.20}})])
    assert b.cash == pytest.approx(20000.0)
    assert b.positions["AMD"] == pytest.approx(100)
    assert b.cost_basis["AMD"] == pytest.approx(138.20)


# ── fills: cash, shares, average cost, realized P&L ───────────────────

def test_buy_moves_cash_and_sets_cost_basis():
    b = replay([genesis(), run("2026-08-15", [fill("AMD", "buy", 70, 143.07, 5.01)])])
    assert b.cash == pytest.approx(100000.0 - 70 * 143.07 - 5.01)
    assert b.positions["AMD"] == pytest.approx(70)
    assert b.cost_basis["AMD"] == pytest.approx(143.07)
    assert b.realized_pnl == pytest.approx(0.0)


def test_second_buy_is_weighted_average_cost():
    b = replay([genesis(),
                run("2026-08-15", [fill("AMD", "buy", 70, 143.07)]),
                run("2026-08-16", [fill("AMD", "buy", 30, 150.0, date="2026-08-16")])])
    assert b.positions["AMD"] == pytest.approx(100)
    assert b.cost_basis["AMD"] == pytest.approx((70 * 143.07 + 30 * 150.0) / 100)


def test_sell_realizes_pnl_net_of_cost_and_keeps_avg_cost():
    b = replay([genesis(),
                run("2026-08-15", [fill("AMD", "buy", 100, 145.0)]),
                run("2026-08-16", [fill("AMD", "sell", 40, 160.0, cost=2.0,
                                        date="2026-08-16")])])
    assert b.positions["AMD"] == pytest.approx(60)
    assert b.cost_basis["AMD"] == pytest.approx(145.0)          # unchanged on a sell
    assert b.realized_pnl == pytest.approx((160.0 - 145.0) * 40 - 2.0)


def test_sell_to_flat_resets_cost_basis():
    b = replay([genesis(),
                run("2026-08-15", [fill("AMD", "buy", 100, 145.0)]),
                run("2026-08-16", [fill("AMD", "sell", 100, 170.0, date="2026-08-16")])])
    assert b.positions["AMD"] == pytest.approx(0.0)
    assert b.cost_basis["AMD"] == pytest.approx(0.0)
    assert b.realized_pnl == pytest.approx((170.0 - 145.0) * 100)


# ── replay == incremental ─────────────────────────────────────────────

def test_replay_equals_incremental_application():
    events = [genesis(),
              run("2026-08-15", [fill("AMD", "buy", 70, 143.07),
                                 fill("NVDA", "buy", 10, 400.0)]),
              run("2026-08-16", [fill("AMD", "sell", 20, 150.0, date="2026-08-16")])]
    whole = replay(events)
    step = Book()
    for e in events:
        apply_event(step, e)
    assert books_equal(whole, step)


# ── mark-to-market ────────────────────────────────────────────────────

def test_mark_to_market_totals_cash_plus_positions():
    b = replay([genesis(50000.0), run("2026-08-15", [fill("AMD", "buy", 100, 140.0)])])
    m = mark_to_market(b, {"AMD": 150.0})
    assert m["positions_value"] == pytest.approx(100 * 150.0)
    assert m["total"] == pytest.approx(b.cash + 100 * 150.0)


def test_mark_skips_positions_without_a_price():
    b = replay([genesis(), run("2026-08-15", [fill("XYZ", "buy", 5, 10.0)])])
    m = mark_to_market(b, {})   # no price for XYZ
    assert m["positions_value"] == pytest.approx(0.0)


# ── order ids + idempotency ───────────────────────────────────────────

def test_order_id_is_deterministic_and_formatted():
    assert order_id("2026-08-16", "AMD", "buy", 70) == "2026-08-16:AMD:buy:70"
    assert order_id("2026-08-16", "AMD", "buy", 70.0) == order_id("2026-08-16", "AMD", "buy", 70)


def test_has_trade_date_detects_a_recorded_day():
    events = [genesis(), run("2026-08-15", [])]
    assert has_trade_date(events, "2026-08-15") is True
    assert has_trade_date(events, "2026-08-16") is False


# ── the invariant ─────────────────────────────────────────────────────

def test_invariant_holds_for_the_true_snapshot():
    events = [genesis(), run("2026-08-15", [fill("AMD", "buy", 70, 143.07, 5.01)])]
    assert invariant_holds(events, replay(events)) is True


def test_invariant_fails_on_a_corrupted_snapshot():
    events = [genesis(), run("2026-08-15", [fill("AMD", "buy", 70, 143.07, 5.01)])]
    bad = replay(events)
    bad.cash += 1.0                      # snapshot drifted from the ledger
    assert invariant_holds(events, bad) is False


# ── append-only correction ────────────────────────────────────────────

def test_compensation_reverses_a_fill_without_editing_history():
    events = [genesis(),
              run("2026-08-15", [fill("AMD", "buy", 70, 143.0, 5.0)]),
              {"type": "compensation", "reverses": "2026-08-15:AMD:buy:70",
               "fills": [fill("AMD", "sell", 70, 143.0, date="2026-08-15")]}]
    b = replay(events)
    assert b.positions["AMD"] == pytest.approx(0.0)
    assert b.cash == pytest.approx(100000.0 - 5.0)   # the erroneous buy's cost stays real
    assert b.realized_pnl == pytest.approx(0.0)
