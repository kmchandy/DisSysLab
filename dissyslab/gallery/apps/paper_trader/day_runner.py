"""
day_runner.py -- the transactional orchestrator: one trading day, start to finish.

Because every decision stage is a tested pure module, the office does not need a
long chain of message-passing agents. It collapses to one atomic day transaction,
which is also what keeps read-decide-commit correct under crash/recovery:

    open_book            (start-boundary invariant / heal-in)
    as_of_view           (decide on close[t-1], fill at open[t])   [market_view]
    apply_exits          (pluggable exit policy)                   [exits]
    target_positions     (named sizing policy)                     [risk_sizer]
    generate_orders      (no-trade band, cash constraint, ids)     [order_generator]
    make_fills           (open + cost/slippage)                    [paper_broker]
    commit_day           (end-boundary invariant / fail-stop)      [paper_store]
    -> brief             (holdings, orders + why, fills, equity)

`run_day` does one date; `run_through` replays every uncommitted trading date up
to a target (default the latest in the data) -- that is catch-up *and* fast
historical replay (the whole thing is deterministic and file-backed, so months
run in seconds). Pure except for the paper_store file I/O.

`compute_fn(bars, params) -> [signal_per_bar]` is injected, so this module stays
independent of any particular strategy and is testable with a toy strategy.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Tuple

from exits import apply_exits
from market_view import all_trading_dates, as_of_view
from order_generator import generate_orders
from paper_broker import make_fills
from paper_ledger import Book, apply_event, mark_to_market
from paper_store import commit_day, open_book, read_ledger
from risk_sizer import target_positions


def _initial_equity(genesis: Dict[str, Any]) -> float:
    eq = float(genesis.get("starting_cash", 0.0))
    for pos in (genesis.get("initial_positions") or {}).values():
        eq += float(pos["shares"]) * float(pos.get("cost_basis", 0.0))
    return eq


def run_day(
    history_msg: Dict[str, Any],
    book_dir: str,
    compute_fn: Callable[[List[dict], Dict[str, Any]], List[float]],
    as_of: str,
    params: Optional[Dict[str, Any]] = None,
    vol_lookback: int = 63,
) -> Dict[str, Any]:
    """Process trading date `as_of` and commit it. Idempotent: a date already in
    the ledger is a no-op (returns a brief marked committed=False, reason=already).
    Returns the brief (a structured dict; rendering is the brief sink's job)."""
    history = history_msg.get("history", {}) or {}
    opened = open_book(book_dir)
    genesis = opened.events[0] if opened.events else {}
    policy = genesis.get("policy", {}) or {}
    book = opened.book

    # idempotency: already committed?
    if any(e.get("type") == "run" and e.get("trade_date") == as_of
           for e in opened.events):
        return {"trade_date": as_of, "committed": False, "reason": "already committed",
                "healed": opened.healed}

    view = as_of_view(history, as_of, compute_fn, params, vol_lookback)
    open_t = view["open_t"]

    signals = apply_exits(view["signals"], book.positions, open_t, book, policy)
    equity = mark_to_market(book, open_t)["total"]
    targets = target_positions(signals, equity, open_t, view["vols"], policy)
    orders, reasons = generate_orders(targets, book.positions, open_t,
                                      book.cash, policy, as_of)
    fills, skipped = make_fills(orders, open_t, policy)

    decisions = {}
    for t, rec in reasons.items():
        decisions[t] = {**rec, "signal": signals.get(t, 0.0)}

    run_event = {
        "type": "run", "trade_date": as_of,
        "prices_as_of": {"close_tminus1": view["close_tminus1"], "open_t": open_t},
        "decisions": decisions,
        "fills": fills,
        "receipt": {k: policy.get(k) for k in
                    ("sizing", "cost_bps", "slippage_bps", "stop_pct",
                     "exit_policy", "no_trade_band")},
    }

    new_book = Book(book.cash, dict(book.positions), dict(book.cost_basis),
                    book.realized_pnl)
    apply_event(new_book, run_event)

    post = mark_to_market(new_book, open_t)
    run_event["equity_after"] = {
        "cash": new_book.cash, "positions_value": post["positions_value"],
        "total": post["total"], "cum_pnl": post["total"] - _initial_equity(genesis),
    }

    committed = commit_day(book_dir, run_event, new_book)

    holdings = {t: {"shares": committed.positions.get(t, 0.0),
                    "avg_cost": committed.cost_basis.get(t, 0.0),
                    "price": open_t.get(t)}
                for t in committed.positions if abs(committed.positions[t]) > 1e-9}

    return {
        "trade_date": as_of, "committed": True, "healed": opened.healed,
        "holdings": holdings,
        "orders": orders, "fills": fills, "skipped": skipped,
        "decisions": decisions,
        "equity": run_event["equity_after"],
        "receipt": run_event["receipt"],
    }


def run_through(
    history_msg: Dict[str, Any],
    book_dir: str,
    compute_fn: Callable[[List[dict], Dict[str, Any]], List[float]],
    through: Optional[str] = None,
    params: Optional[Dict[str, Any]] = None,
    vol_lookback: int = 63,
) -> List[Dict[str, Any]]:
    """Process every not-yet-committed trading date up to `through` (default: the
    latest date in the data), in order. This is catch-up and fast replay. Returns
    the list of daily briefs actually processed."""
    history = history_msg.get("history", {}) or {}
    dates = all_trading_dates(history)
    if not dates:
        return []
    through = through or dates[-1]

    committed_dates = {e.get("trade_date") for e in read_ledger(book_dir)
                       if e.get("type") == "run"}
    briefs = []
    for d in dates:
        if d > through:
            break
        if d in committed_dates or d == dates[0]:   # skip first date (no prior close)
            continue
        briefs.append(run_day(history_msg, book_dir, compute_fn, d,
                              params=params, vol_lookback=vol_lookback))
    return briefs
