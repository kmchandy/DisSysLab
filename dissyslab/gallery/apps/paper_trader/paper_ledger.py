"""
paper_ledger.py -- the tested, framework-independent core of the paper_trader
book.

Pure Python, no DisSysLab dependency, so it can be unit-tested in isolation.
Everything correctness-critical about the book lives here, in one place:

  * the book is a pure function of the event log       -> replay()
  * the checkpoint-consistency invariant                -> invariant_holds()
      snapshot == replay(ledger)
  * average-cost basis and realized P&L                 -> apply_event()
  * mark-to-market at a given price map (open_t)        -> mark_to_market()
  * deterministic order ids + day-level idempotency     -> order_id(), has_trade_date()

The office roles read and append ledger events; they call into this module for
all book math, so the part that must be correct is small, framework-independent,
and fully tested. Design rationale: see EXECUTION_DESIGN.md (event-sourced ledger,
the invariant, decide-at-close/fill-at-open, average-cost basis).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

_TOL = 1e-6  # money/shares comparison tolerance


@dataclass
class Book:
    """The derived book state -- a pure function of the ledger, never edited in
    place except by applying events."""
    cash: float = 0.0
    positions: Dict[str, float] = field(default_factory=dict)   # ticker -> shares
    cost_basis: Dict[str, float] = field(default_factory=dict)  # ticker -> avg cost / share
    realized_pnl: float = 0.0


def order_id(trade_date: str, ticker: str, side: str, qty: float) -> str:
    """Deterministic order id. Re-deriving the same day's order yields the same
    id, so a replay-after-crash cannot double-place it."""
    q = int(qty) if float(qty).is_integer() else qty
    return f"{trade_date}:{ticker}:{side}:{q}"


def _apply_fill(book: Book, fill: Dict[str, Any]) -> None:
    """Apply one fill in place.

    Convention (see design doc): cost basis is the average *fill price*, excluding
    the transaction cost; the cost is a cash friction that flows through to total
    P&L via cash. Realized P&L on a sell is (price - avg_cost) * qty - cost. Avg
    cost is unchanged by a sell (average-cost method) and resets when the position
    goes flat.
    """
    t = fill["ticker"]
    side = fill["side"]
    qty = float(fill["qty"])
    price = float(fill["fill_price"])
    cost = float(fill.get("cost", 0.0))
    shares = book.positions.get(t, 0.0)
    avg = book.cost_basis.get(t, 0.0)

    if side == "buy":
        book.cash -= qty * price + cost
        new_shares = shares + qty
        book.cost_basis[t] = (
            (shares * avg + qty * price) / new_shares if abs(new_shares) > _TOL else 0.0
        )
        book.positions[t] = new_shares
    elif side == "sell":
        book.cash += qty * price - cost
        book.realized_pnl += (price - avg) * qty - cost
        new_shares = shares - qty
        if abs(new_shares) < _TOL:
            book.positions[t] = 0.0
            book.cost_basis[t] = 0.0
        else:
            book.positions[t] = new_shares
            # avg cost unchanged on a sell (average-cost convention)
    else:
        raise ValueError(f"unknown fill side: {side!r}")


def apply_event(book: Book, event: Dict[str, Any]) -> None:
    """Apply one ledger event in place. Genesis seeds cash + starting holdings;
    a run or a compensation applies its `fills`."""
    etype = event.get("type")
    if etype == "genesis":
        book.cash += float(event.get("starting_cash", 0.0))
        for t, pos in (event.get("initial_positions") or {}).items():
            book.positions[t] = book.positions.get(t, 0.0) + float(pos["shares"])
            book.cost_basis[t] = float(pos.get("cost_basis", 0.0))
    elif etype in ("run", "compensation"):
        for fill in event.get("fills") or []:
            _apply_fill(book, fill)
    else:
        raise ValueError(f"unknown event type: {etype!r}")


def replay(events: List[Dict[str, Any]]) -> Book:
    """The book is a pure function of the ordered event log (genesis first)."""
    book = Book()
    for e in events:
        apply_event(book, e)
    return book


def mark_to_market(book: Book, prices: Dict[str, float]) -> Dict[str, float]:
    """Equity given a price map (marked at open_t by convention). A held position
    with no price contributes 0 rather than crashing the mark."""
    positions_value = 0.0
    for t, shares in book.positions.items():
        if abs(shares) > _TOL and t in prices:
            positions_value += shares * float(prices[t])
    return {
        "cash": book.cash,
        "positions_value": positions_value,
        "total": book.cash + positions_value,
    }


def has_trade_date(events: List[Dict[str, Any]], trade_date: str) -> bool:
    """Day-level idempotency: is this trading day already recorded in the ledger?
    Re-running a recorded day must be a no-op."""
    return any(
        e.get("type") == "run" and e.get("trade_date") == trade_date for e in events
    )


def books_equal(a: Book, b: Book) -> bool:
    """Structural equality within tolerance. Cost basis is compared only where a
    position is actually held (a flat ticker's stale basis is irrelevant)."""
    if abs(a.cash - b.cash) > _TOL or abs(a.realized_pnl - b.realized_pnl) > _TOL:
        return False
    keys = set(a.positions) | set(b.positions)
    for k in keys:
        sa = a.positions.get(k, 0.0)
        sb = b.positions.get(k, 0.0)
        if abs(sa - sb) > _TOL:
            return False
        if abs(sa) > _TOL and abs(a.cost_basis.get(k, 0.0) - b.cost_basis.get(k, 0.0)) > _TOL:
            return False
    return True


def invariant_holds(events: List[Dict[str, Any]], snapshot: Book) -> bool:
    """The checkpoint-consistency invariant: snapshot == replay(ledger). Checked
    at both run boundaries; the caller applies heal-in / fail-stop-out."""
    return books_equal(replay(events), snapshot)
