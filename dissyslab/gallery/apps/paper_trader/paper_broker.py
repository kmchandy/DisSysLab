"""
paper_broker.py -- FILL: simulate paper executions. Orders + the day's OPEN
prices + the cost model -> fills. Pure Python, cloud-testable.

STRICTLY paper: no brokerage, no credentials, no real orders -- fills are
simulated and written only to the local ledger.

Fill price is the open, adjusted by slippage (a buy pays up, a sell receives
less). Transaction cost is `cost_bps` on the traded notional -- the backtester's
cost model, applied at the fill. MVP defaults: slippage 0 bps (exact reuse of the
backtester's cost model), cost 5 bps. An order for a ticker with no open price is
skipped, not guessed.
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple


def make_fills(
    orders: List[Dict[str, Any]],
    prices: Dict[str, float],
    policy: Dict[str, Any],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Return (fills, skipped).

    Each fill: {order_id, ticker, side, qty, fill_price, cost, cash_delta}.
    `cash_delta` is a convenience/cross-check; the ledger recomputes cash from
    fill_price + cost, so the two must agree (there is a test for that).
    """
    cost_rate = float(policy.get("cost_bps", 0.0)) / 1e4
    slip = float(policy.get("slippage_bps", 0.0)) / 1e4
    fills: List[Dict[str, Any]] = []
    skipped: List[Dict[str, Any]] = []

    for o in orders:
        t, side, qty = o["ticker"], o["side"], float(o["qty"])
        if t not in prices:
            skipped.append({**o, "reason": "no open price"})
            continue
        base = float(prices[t])
        fill_price = base * (1.0 + slip) if side == "buy" else base * (1.0 - slip)
        notional = qty * fill_price
        cost = cost_rate * notional
        cash_delta = (-notional - cost) if side == "buy" else (notional - cost)
        fills.append({"order_id": o["order_id"], "ticker": t, "side": side,
                      "qty": qty, "fill_price": fill_price, "cost": cost,
                      "cash_delta": cash_delta})

    return fills, skipped
