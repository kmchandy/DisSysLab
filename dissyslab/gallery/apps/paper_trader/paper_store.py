"""
paper_store.py -- durable book store + the day-atomic commit transaction +
invariant enforcement.

Pure Python (stdlib only), so the transaction and recovery behavior are fully
unit-testable without the framework, including *simulated crashes*. The DisSysLab
roles (current_book source, portfolio_updater, ledger_writer sink) are thin
wrappers over these functions -- all correctness lives here.

Files per book directory:
  ledger.jsonl  -- append-only event log (source of truth), one JSON object/line
  book.json     -- derived snapshot cache (always rebuildable from the ledger)

One trading day is one transaction:

  open_book(dir)   -> load ledger + snapshot; START-boundary invariant:
                      missing snapshot  -> rebuild from ledger (fresh cache);
                      snapshot mismatch -> HEAL-IN: rebuild from ledger, warn.

  commit_day(dir, run_event, new_book)
                   -> idempotent on trade_date (re-running a recorded day is a
                      no-op); END-boundary invariant: new_book must equal
                      replay(ledger + run_event) or FAIL-STOP (raise, nothing
                      written). On success: append run_event to ledger.jsonl
                      (the commit point), then write book.json. A crash between
                      the two is healed by the next open_book.

See EXECUTION_DESIGN.md for the rationale (event-sourced ledger, the invariant,
heal-in / fail-stop-out, day-level idempotency).
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, NamedTuple, Optional

from paper_ledger import Book, books_equal, has_trade_date, replay

LEDGER_NAME = "ledger.jsonl"
BOOK_NAME = "book.json"


class InvariantError(Exception):
    """Raised at the end-of-run boundary when the updated book disagrees with
    replay(ledger) -- the office must halt, not commit (fail-stop-out)."""


class OpenResult(NamedTuple):
    events: List[Dict[str, Any]]
    book: Book
    healed: bool       # snapshot was stale/corrupt and rebuilt from the ledger
    rebuilt: bool      # snapshot was missing and rebuilt from the ledger


# ── paths ─────────────────────────────────────────────────────────────

def _ledger_path(d: str) -> str:
    return os.path.join(d, LEDGER_NAME)


def _book_path(d: str) -> str:
    return os.path.join(d, BOOK_NAME)


# ── (de)serialization ─────────────────────────────────────────────────

def book_to_dict(book: Book, **extra: Any) -> Dict[str, Any]:
    d = {"cash": book.cash, "positions": dict(book.positions),
         "cost_basis": dict(book.cost_basis), "realized_pnl": book.realized_pnl}
    d.update(extra)
    return d


def book_from_dict(d: Dict[str, Any]) -> Book:
    return Book(cash=float(d.get("cash", 0.0)),
               positions={k: float(v) for k, v in (d.get("positions") or {}).items()},
               cost_basis={k: float(v) for k, v in (d.get("cost_basis") or {}).items()},
               realized_pnl=float(d.get("realized_pnl", 0.0)))


# ── reads ─────────────────────────────────────────────────────────────

def read_ledger(d: str) -> List[Dict[str, Any]]:
    """Read the append-only event log. Missing file -> empty (no book yet)."""
    path = _ledger_path(d)
    if not os.path.exists(path):
        return []
    events: List[Dict[str, Any]] = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                events.append(json.loads(line))
    return events


def read_snapshot(d: str) -> Optional[Book]:
    path = _book_path(d)
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return book_from_dict(json.load(f))


# ── atomic writes ─────────────────────────────────────────────────────

def _append_event(d: str, event: Dict[str, Any]) -> None:
    """Append one event as a JSON line, flushed and fsync'd -- the commit point."""
    with open(_ledger_path(d), "a", encoding="utf-8") as f:
        f.write(json.dumps(event) + "\n")
        f.flush()
        os.fsync(f.fileno())


def _write_snapshot(d: str, book: Book, **extra: Any) -> None:
    """Atomically (temp + rename) write the derived snapshot cache."""
    path = _book_path(d)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(book_to_dict(book, **extra), f, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


# ── lifecycle ─────────────────────────────────────────────────────────

def create_book(d: str, genesis: Dict[str, Any]) -> Book:
    """Initialize a new book directory: genesis becomes the first ledger line and
    seeds the snapshot. Refuses to clobber an existing ledger."""
    os.makedirs(d, exist_ok=True)
    if os.path.exists(_ledger_path(d)) and read_ledger(d):
        raise FileExistsError(f"book already exists in {d}")
    _append_event(d, genesis)
    book = replay([genesis])
    _write_snapshot(d, book, as_of_trade_date=genesis.get("first_trade_date"))
    return book


def open_book(d: str) -> OpenResult:
    """Load the book at run start and enforce the START-boundary invariant.

    - snapshot missing  -> rebuild from the ledger (rebuilt=True).
    - snapshot != replay -> HEAL-IN: rebuild from the ledger, healed=True (warn).
    - otherwise the snapshot is trusted.
    The ledger is always the source of truth; a bad snapshot never blocks a run.
    """
    events = read_ledger(d)
    replayed = replay(events)
    snapshot = read_snapshot(d)
    if snapshot is None:
        _write_snapshot(d, replayed)
        return OpenResult(events, replayed, healed=False, rebuilt=True)
    if not books_equal(snapshot, replayed):
        _write_snapshot(d, replayed)
        return OpenResult(events, replayed, healed=True, rebuilt=False)
    return OpenResult(events, snapshot, healed=False, rebuilt=False)


def commit_day(d: str, run_event: Dict[str, Any], new_book: Book) -> Book:
    """Commit one trading day.

    - Idempotent: if trade_date is already recorded, no-op (return the current
      book) -- safe re-run and catch-up.
    - END-boundary invariant: new_book (the incrementally-updated book) must equal
      replay(ledger + run_event); otherwise FAIL-STOP (raise InvariantError,
      nothing written).
    - On success: append run_event to the ledger (COMMIT POINT), then write the
      snapshot. A crash between the two heals on the next open_book.
    """
    trade_date = run_event.get("trade_date")
    events = read_ledger(d)
    if trade_date is not None and has_trade_date(events, trade_date):
        return replay(events)                      # already committed -> no-op

    expected = replay(events + [run_event])
    if not books_equal(new_book, expected):
        raise InvariantError(
            f"end-of-run invariant failed for {trade_date}: updated book != "
            f"replay(ledger + run); refusing to commit"
        )

    _append_event(d, run_event)                    # commit point (durable)
    _write_snapshot(d, expected, as_of_trade_date=trade_date)
    return expected
