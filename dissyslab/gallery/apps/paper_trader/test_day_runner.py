"""
End-to-end test of the whole paper-trader loop via day_runner -- multi-day
historical replay, idempotency, and catch-up -- all in the cloud with real files
and a toy strategy:

    python3 -m pytest test_day_runner.py -q
"""

from __future__ import annotations

import pytest

from day_runner import run_day, run_through
from paper_ledger import invariant_holds
from paper_store import create_book, open_book, read_ledger

DATES = [f"2020-01-{i:02d}" for i in range(1, 13)]        # 12 trading days


def make_history():
    def bars(opens, closes):
        return [{"date": d, "open": o, "high": c, "low": o, "close": c, "volume": 0}
                for d, o, c in zip(DATES, opens, closes)]
    a_close = [100 + i for i in range(12)]                # strictly rising
    b_close = [50 + i for i in range(12)]
    return {"type": "stock_history",
            "history": {"A": bars([c - 0.5 for c in a_close], a_close),
                        "B": bars([c - 0.25 for c in b_close], b_close)}}


def sma_cross(bars, params):
    closes = [b["close"] for b in bars]
    m = sum(closes) / len(closes)
    return [1.0 if c > m else 0.0 for c in closes]


def genesis(cash=100000.0):
    return {"type": "genesis", "schema_version": 1, "book_id": "paper:test",
            "strategy": "sma_cross", "first_trade_date": DATES[0],
            "starting_cash": cash, "universe": ["A", "B"], "initial_positions": {},
            "policy": {"sizing": "equal_weight", "no_trade_band": 0.005,
                       "cost_bps": 0.0, "slippage_bps": 0.0, "stop_pct": 0.10,
                       "exit_policy": "market_defined"}}


def test_full_replay_invests_and_stays_consistent(tmp_path):
    d = str(tmp_path / "book")
    create_book(d, genesis())
    hist = make_history()

    briefs = run_through(hist, d, sma_cross)
    assert briefs, "should have processed trading days"
    assert briefs[-1]["committed"] is True

    # the strategy turns long as prices rise -> the book ends invested
    book = open_book(d).book
    assert book.positions.get("A", 0) > 0 and book.positions.get("B", 0) > 0
    assert book.cash < 100000.0

    # the ledger is consistent with the snapshot at every point
    assert invariant_holds(read_ledger(d), book)
    # one run event per processed trading day (all dates after the first)
    runs = [e for e in read_ledger(d) if e.get("type") == "run"]
    assert len(runs) == len(DATES) - 1


def test_replay_is_idempotent(tmp_path):
    d = str(tmp_path / "book")
    create_book(d, genesis())
    hist = make_history()
    run_through(hist, d, sma_cross)
    n = len(read_ledger(d))
    again = run_through(hist, d, sma_cross)       # nothing new to do
    assert again == [] and len(read_ledger(d)) == n


def test_catch_up_processes_missed_days_in_order(tmp_path):
    d = str(tmp_path / "book")
    create_book(d, genesis())
    hist = make_history()

    # run only through the middle, then catch up to the end
    run_through(hist, d, sma_cross, through=DATES[5])
    mid = len([e for e in read_ledger(d) if e.get("type") == "run"])
    run_through(hist, d, sma_cross)               # through = latest
    end = len([e for e in read_ledger(d) if e.get("type") == "run"])
    assert 0 < mid < end == len(DATES) - 1


def test_single_day_re_run_is_a_no_op(tmp_path):
    d = str(tmp_path / "book")
    create_book(d, genesis())
    hist = make_history()
    b1 = run_day(hist, d, sma_cross, DATES[6])
    assert b1["committed"] is True
    b2 = run_day(hist, d, sma_cross, DATES[6])    # same day again
    assert b2["committed"] is False and b2["reason"] == "already committed"
