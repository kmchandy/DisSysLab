"""
Tests for the durable book store + day-atomic commit + invariant enforcement.
Pure Python with real files in a tmp dir, so recovery is tested for real:

    python3 -m pytest test_paper_store.py -q

Covers the commit transaction, day-level idempotency, missing/stale snapshot
recovery (heal-in), a simulated crash between ledger-append and snapshot-write,
and end-of-run fail-stop.
"""

from __future__ import annotations

import os

import pytest

from paper_ledger import order_id, replay
from paper_store import (
    InvariantError,
    _append_event,
    commit_day,
    create_book,
    open_book,
    read_ledger,
    read_snapshot,
)


def genesis(cash=100000.0):
    return {"type": "genesis", "starting_cash": cash, "initial_positions": {},
            "first_trade_date": "2026-08-14"}


def run_event(date, fills):
    return {"type": "run", "trade_date": date, "fills": fills}


def fill(t, side, qty, price, cost=0.0, date="2026-08-15"):
    return {"order_id": order_id(date, t, side, qty), "ticker": t, "side": side,
            "qty": qty, "fill_price": price, "cost": cost}


def _commit(d, ev):
    """Commit with the correctly-derived book (the happy path)."""
    expected = replay(read_ledger(d) + [ev])
    return commit_day(d, ev, expected)


# ── create / open ─────────────────────────────────────────────────────

def test_create_book_seeds_ledger_and_snapshot(tmp_path):
    d = str(tmp_path / "book")
    create_book(d, genesis(100000.0))
    assert len(read_ledger(d)) == 1
    assert read_snapshot(d).cash == pytest.approx(100000.0)


def test_create_book_refuses_to_clobber(tmp_path):
    d = str(tmp_path / "book")
    create_book(d, genesis())
    with pytest.raises(FileExistsError):
        create_book(d, genesis())


def test_open_book_trusts_a_consistent_snapshot(tmp_path):
    d = str(tmp_path / "book")
    create_book(d, genesis())
    r = open_book(d)
    assert not r.healed and not r.rebuilt


# ── commit ────────────────────────────────────────────────────────────

def test_commit_day_writes_ledger_and_snapshot(tmp_path):
    d = str(tmp_path / "book")
    create_book(d, genesis())
    book = _commit(d, run_event("2026-08-15", [fill("AMD", "buy", 70, 143.0, 5.0)]))
    assert len(read_ledger(d)) == 2
    assert read_snapshot(d).positions["AMD"] == pytest.approx(70)
    assert book.cash == pytest.approx(100000.0 - 70 * 143.0 - 5.0)


def test_commit_day_is_idempotent_on_trade_date(tmp_path):
    d = str(tmp_path / "book")
    create_book(d, genesis())
    ev = run_event("2026-08-15", [fill("AMD", "buy", 70, 143.0)])
    _commit(d, ev)
    n = len(read_ledger(d))
    _commit(d, ev)                      # re-run the same day
    assert len(read_ledger(d)) == n     # no-op


def test_commit_multiple_days_in_order(tmp_path):
    d = str(tmp_path / "book")
    create_book(d, genesis())
    for date, px in [("2026-08-15", 143.0), ("2026-08-16", 150.0)]:
        _commit(d, run_event(date, [fill("AMD", "buy", 10, px, date=date)]))
    assert len(read_ledger(d)) == 3
    assert open_book(d).book.positions["AMD"] == pytest.approx(20)


# ── recovery / invariant ──────────────────────────────────────────────

def test_open_book_rebuilds_a_missing_snapshot(tmp_path):
    d = str(tmp_path / "book")
    create_book(d, genesis())
    os.remove(os.path.join(d, "book.json"))       # lost the cache
    r = open_book(d)
    assert r.rebuilt and not r.healed
    assert r.book.cash == pytest.approx(100000.0)
    assert read_snapshot(d) is not None            # rebuilt on disk


def test_open_book_heals_after_a_crash_between_append_and_snapshot(tmp_path):
    """Simulate a crash mid-commit: the run event reached the ledger, but the
    snapshot was never updated. The next open_book must recover from the ledger."""
    d = str(tmp_path / "book")
    create_book(d, genesis())
    ev = run_event("2026-08-15", [fill("AMD", "buy", 70, 143.0)])
    _append_event(d, ev)                           # ledger advanced...
    # ...crash here: snapshot still reflects only genesis
    r = open_book(d)
    assert r.healed
    assert r.book.positions["AMD"] == pytest.approx(70)         # recovered
    assert read_snapshot(d).positions["AMD"] == pytest.approx(70)  # cache repaired


def test_commit_day_fail_stops_on_an_inconsistent_book(tmp_path):
    d = str(tmp_path / "book")
    create_book(d, genesis())
    ev = run_event("2026-08-15", [fill("AMD", "buy", 70, 143.0)])
    bad = replay(read_ledger(d) + [ev])
    bad.cash += 999.0                              # updated book disagrees with replay
    with pytest.raises(InvariantError):
        commit_day(d, ev, bad)
    assert len(read_ledger(d)) == 1                # nothing committed
