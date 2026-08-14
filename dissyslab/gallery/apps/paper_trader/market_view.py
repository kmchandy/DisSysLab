"""
market_view.py -- the pure core of the `market_today` source + `SIGNAL` adapter.

Given per-ticker daily bars and an "as-of" trading date, produce everything the
decision path needs for that day, under the decide-at-close(t-1) / fill-at-open(t)
convention:

  * signals[t]        -- the strategy's latest signal, computed from bars up to
                         the *prior* close (no look-ahead)
  * vols[t]           -- annualized volatility over a lookback (for inverse-vol
                         sizing), also from bars up to the prior close
  * open_t[t]         -- the open on the as-of date (the fill price)
  * close_tminus1[t]  -- the prior close (what the decision was made on)

`as_of` defaults to the real today in the live source, but is a *parameter*, so
the whole office can be replayed over historical dates fast -- months of behavior
in seconds -- which is how you test it without waiting real days. This module is
generic over the strategy's `compute_fn(bars, params) -> [signal_per_bar]`, so it
is pure and testable independent of any particular strategy or the framework.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

_TRADING_DAYS = 252


def all_trading_dates(history: Dict[str, List[dict]]) -> List[str]:
    dates = {b["date"] for bars in history.values() for b in bars if b.get("date")}
    return sorted(dates)


def _returns(closes: List[float]) -> List[float]:
    out = []
    for i in range(1, len(closes)):
        p, c = closes[i - 1], closes[i]
        if p:
            out.append(c / p - 1.0)
    return out


def _annualized_vol(bars: List[dict], lookback: int) -> Optional[float]:
    closes = [b["close"] for b in bars if b.get("close") is not None]
    rets = _returns(closes)[-lookback:]
    n = len(rets)
    if n < 2:
        return None
    mean = sum(rets) / n
    var = sum((r - mean) ** 2 for r in rets) / (n - 1)
    return (var ** 0.5) * (_TRADING_DAYS ** 0.5)


def as_of_view(
    history: Dict[str, List[dict]],
    as_of: str,
    compute_fn: Callable[[List[dict], Dict[str, Any]], List[float]],
    params: Optional[Dict[str, Any]] = None,
    vol_lookback: int = 63,
) -> Dict[str, Any]:
    """Build the market view for trading date `as_of`. Raises if `as_of` is not a
    trading date or is the first date (no prior close to decide on)."""
    params = params or {}
    dates = all_trading_dates(history)
    if as_of not in dates:
        raise ValueError(f"{as_of} is not a trading date in the data")
    idx = dates.index(as_of)
    if idx == 0:
        raise ValueError(f"{as_of} is the first date; no prior close to decide on")
    cutoff = dates[idx - 1]

    signals: Dict[str, float] = {}
    vols: Dict[str, Optional[float]] = {}
    open_t: Dict[str, float] = {}
    close_tminus1: Dict[str, float] = {}

    for ticker, bars in history.items():
        bars = sorted(bars, key=lambda b: b["date"])
        decision = [b for b in bars if b["date"] <= cutoff]
        if len(decision) < 2:
            continue                                   # not enough history yet
        sig = compute_fn(decision, params)
        signals[ticker] = float(sig[-1]) if sig else 0.0
        vols[ticker] = _annualized_vol(decision, vol_lookback)
        close_tminus1[ticker] = decision[-1]["close"]
        today = [b for b in bars if b["date"] == as_of]
        if today and today[0].get("open") is not None:
            open_t[ticker] = today[0]["open"]

    return {"trade_date": as_of, "signals": signals, "vols": vols,
            "open_t": open_t, "close_tminus1": close_tminus1}
