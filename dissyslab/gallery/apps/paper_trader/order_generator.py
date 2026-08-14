"""
order_generator.py -- RECON: turn desired target positions into the orders needed
to get there from what is currently held. Pure Python, cloud-testable.

Applies, in order:
  * the no-trade band -- skip deltas too small to be worth trading, measured as a
    fraction of equity (churn control, the same band the backtester uses);
  * a cash constraint -- sells free cash first, then buys are filled in a
    deterministic order and trimmed to fit remaining cash;
  * deterministic order ids, so a replay-after-crash cannot double-place.

Cost is NOT applied here -- that is paper_broker's job at the fill. This module
only decides *what* to trade, and records a per-ticker reason for the decision
trace.
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from paper_ledger import order_id

_EPS = 1e-9


def generate_orders(
    targets: Dict[str, float],
    positions: Dict[str, float],
    prices: Dict[str, float],
    cash: float,
    policy: Dict[str, Any],
    trade_date: str,
) -> Tuple[List[Dict[str, Any]], Dict[str, Dict[str, Any]]]:
    """Return (orders, reasons).

    orders:  [{"order_id","ticker","side","qty"}]
    reasons: {ticker: {"target","current","delta","order","reason"}} -- the
             decision-trace fragment for the ledger.
    """
    band = float(policy.get("no_trade_band", 0.0))
    equity = cash + sum(
        positions.get(t, 0.0) * prices[t] for t in positions if t in prices
    )
    band_dollars = band * equity

    reasons: Dict[str, Dict[str, Any]] = {}
    buys: List[Dict[str, Any]] = []
    sells: List[Dict[str, Any]] = []

    for t in sorted(set(targets) | set(positions)):
        cur = float(positions.get(t, 0.0))
        tgt = float(targets.get(t, 0.0))
        delta = tgt - cur
        rec: Dict[str, Any] = {"target": tgt, "current": cur, "delta": delta,
                               "order": None}
        if t not in prices:
            rec["reason"] = "no price; skipped"
        elif abs(delta) < _EPS:
            rec["reason"] = "hold (at target)"
        elif abs(delta * prices[t]) < band_dollars:
            rec["reason"] = "hold (within no-trade band)"
        else:
            side = "buy" if delta > 0 else "sell"
            (buys if side == "buy" else sells).append(
                {"ticker": t, "side": side, "qty": abs(delta), "price": prices[t]}
            )
            rec["reason"] = "candidate " + side
        reasons[t] = rec

    orders: List[Dict[str, Any]] = []

    # sells always execute and free cash first
    for s in sells:
        orders.append(_mk(trade_date, s["ticker"], "sell", s["qty"]))
        reasons[s["ticker"]].update(
            {"reason": "sell/exit", "order": {"side": "sell", "qty": s["qty"]}}
        )
    available = cash + sum(s["qty"] * s["price"] for s in sells)

    # buys in a deterministic order, trimmed to fit remaining cash
    for b in sorted(buys, key=lambda x: x["ticker"]):
        t, price = b["ticker"], b["price"]
        notional = b["qty"] * price
        if notional <= available + _EPS:
            qty = b["qty"]
            available -= notional
        else:
            qty = max(0.0, available / price)
            available -= qty * price
            if qty < _EPS:
                reasons[t].update({"reason": "skipped (insufficient cash)",
                                   "order": None})
                continue
            reasons[t]["reason"] = "buy (trimmed to fit cash)"
        orders.append(_mk(trade_date, t, "buy", qty))
        reasons[t]["order"] = {"side": "buy", "qty": qty}

    return orders, reasons


def _mk(trade_date: str, ticker: str, side: str, qty: float) -> Dict[str, Any]:
    return {"order_id": order_id(trade_date, ticker, side, qty),
            "ticker": ticker, "side": side, "qty": qty}
