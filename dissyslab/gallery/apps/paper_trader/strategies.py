"""
strategies.py -- per-ticker strategy compute functions for the paper trader.

Contract (matches market_view / day_runner): fn(bars, params) -> [signal_per_bar],
where signal[t] depends only on bars[0..t] (no look-ahead).

MVP: a moving-average crossover (the same formula as the backtester's `mac`).
NOTE: this currently *duplicates* the backtester's mac compute. Unifying the two
into one shared strategy module is on the consistency backlog
(EXECUTION_DESIGN.md, §4) -- until then, keep this identical to the backtester's
`_mac_compute_variant_signal` so live and backtest agree. Only per-ticker
strategies are supported here; context/cross-sectional strategies (relative
strength) need the cross-section threaded through market_view and are a later
enhancement.
"""

from __future__ import annotations

from typing import Callable, Dict, List, Tuple


def _ewma(prices: List[float], span: int) -> List[float]:
    alpha = 2.0 / (span + 1.0)
    out = [prices[0]]
    for p in prices[1:]:
        out.append(alpha * p + (1.0 - alpha) * out[-1])
    return out


def mac_crossover(bars: List[dict], params: Tuple[int, int]) -> List[float]:
    """+1 when the fast EWMA is above the slow, -1 otherwise (always in the
    market, long or short)."""
    fast_span, slow_span = params
    closes = [b["close"] for b in bars]
    fast, slow = _ewma(closes, fast_span), _ewma(closes, slow_span)
    return [1.0 if f > s else -1.0 for f, s in zip(fast, slow)]


# Keep these spans identical to the backtester's MAC_VARIANTS when unifying.
MAC_VARIANTS: Dict[str, Tuple[int, int]] = {
    "mac_fast": (8, 32), "mac_med_fast": (16, 64), "mac_med": (32, 128),
    "mac_med_slow": (48, 192), "mac_slow": (64, 256),
}


def resolve(strategy: str) -> Tuple[Callable[[List[dict], object], List[float]], object]:
    """Return (compute_fn, params) for a named strategy."""
    if strategy in MAC_VARIANTS:
        return mac_crossover, MAC_VARIANTS[strategy]
    raise ValueError(f"unknown strategy {strategy!r}; known: {sorted(MAC_VARIANTS)}")
