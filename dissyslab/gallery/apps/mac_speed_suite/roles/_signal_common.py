# dissyslab/gallery/apps/mac_speed_suite/roles/_signal_common.py
# Shared helper -- underscore prefix so load_roles_dir skips it as a
# role file (same convention as _backtester_core.py).

"""
Shared signal-computer wrapper + factory, used by every strategy family
(MAC, Donchian, Turtle, and any future strategy) in this office.

This is the generalized version of the 3-part contract worked out
before any of this was built: (1) a VARIANTS table, (2) a per-ticker
compute function, (3) a shared wrapper. BACKTESTER and EVALUATOR need
zero changes to support a new strategy family -- only a new
`compute_variant_signal` needs to be written. Confirmed in practice,
not just in design: adding Donchian and Turtle alongside MAC required
no changes anywhere downstream of this module.

The three-part contract
========================
1. VARIANTS: Dict[str, Any] -- variant name -> whatever parameters
   that strategy family's compute function needs (MAC's
   (fast_span, slow_span) tuple; Donchian's breakout window in days;
   Turtle's dict of entry/exit/atr periods, max pyramided units, and
   stop-loss multiple).

2. compute_variant_signal(bars, params) -> List[float]: the one
   strategy-specific piece. `bars` is a ticker's full list of daily bar
   dicts (date/open/high/low/close/volume) -- not just closes, so a
   strategy that needs the day's high/low (Donchian, Turtle) can use
   them, while one that only needs closes (MAC) can ignore the rest.
   Contract: signal[t] must depend only on bars[0..t] (no lookahead) --
   this is on the compute function's author to uphold; it is not
   mechanically enforced by this module.

   The returned signal is a *position size*, not just a direction:
   +1.0 / -1.0 for a strategy that's always fully long or fully short
   (MAC, Donchian here), or a fractional value in between for a
   strategy that scales its position in and out (Turtle's pyramided
   units, here in steps of 1/max_units times sign). BACKTESTER's math
   (`prior_signal * today_return`) already handles a continuous value
   correctly -- confirmed by running Turtle through the unmodified
   BACKTESTER, not just reasoned about.

3. The wrapper below (`make_signal_computer`'s inner `signal_computer`):
   shared, written once. Per ticker: extracts closes, computes
   day-over-day returns and annualized volatility (a property of the
   stock, not of any one strategy or variant), then loops every variant
   calling that strategy family's `compute_variant_signal`, and
   assembles the message.

Variant names are prefixed with the strategy family's own name (e.g.
"mac_fast", "donchian_20", "turtle_s1") before being placed in the
output message, so several strategy families' SIGNAL_COMPUTERs can all
feed the same JOIN/EVALUATOR without their variant names colliding.

Input message shape (from any registered `*_stock_history` source):
    {
        "type":    "stock_history",
        "tickers": ["AMD", "NFLX", ...],
        "history": {
            "AMD": [{"date": "2025-08-01", "open": ..., "high": ...,
                     "low": ..., "close": ..., "volume": ...}, ...],
            ...
        },
        ...
    }

Output message shape:
    {
        "type":     "trend_signals",
        "tickers":  [...],
        "variants": ["mac_fast", ..., "donchian_20", ..., "turtle_s1", ...],
        "series": {
            "AMD": {
                "dates":   [...],
                "returns": [None, 0.0031, ...],
                "signals": {"mac_fast": [...], "donchian_20": [...], ...},
            },
            ...
        },
        "ticker_volatility": {"AMD": 0.44, ...},
    }
"""

import inspect
from typing import Any, Callable, Dict, List, Optional

TRADING_DAYS_PER_YEAR = 252.0


def _accepts_context(fn: Callable) -> bool:
    """Whether a strategy's compute function opts into cross-sectional
    context. Existing per-ticker strategies keep the two-argument signature
    ``(bars, params)`` and are called exactly as before; a strategy that
    declares ``(bars, params, context)`` (or a ``context`` keyword) is handed
    a per-ticker context dict (market series + this ticker's relative-strength
    rank/percentile), enabling relative-strength rules without touching any
    other strategy or the shared machinery downstream."""
    try:
        params = list(inspect.signature(fn).parameters.values())
    except (TypeError, ValueError):
        return False
    if any(p.name == "context" for p in params):
        return True
    positional = [p for p in params
                  if p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)]
    return len(positional) >= 3


def _daily_returns(closes: List[float]) -> List[Optional[float]]:
    """Day-over-day simple returns. Day 0 has no prior day -> None."""
    returns: List[Optional[float]] = [None]
    for prev, cur in zip(closes, closes[1:]):
        returns.append((cur - prev) / prev if prev else None)
    return returns


def _annualized_volatility(returns: List[Optional[float]]) -> float:
    """Sample std of the stock's own raw-price returns, annualized. A
    property of the stock, not of any one strategy -- computed once per
    ticker here rather than separately inside every variant/strategy."""
    values = [r for r in returns if r is not None]
    n = len(values)
    if n < 2:
        return 0.0
    mean = sum(values) / n
    variance = sum((r - mean) ** 2 for r in values) / (n - 1)
    return (variance ** 0.5) * (TRADING_DAYS_PER_YEAR ** 0.5)


def make_signal_computer(
    strategy_name: str,
    variants: Dict[str, Any],
    compute_variant_signal: Callable[[List[dict], Any], List[float]],
) -> Callable[[Dict[str, Any]], list]:
    """
    Factory: builds a SIGNAL_COMPUTER worker body for one strategy family.

    Args:
        strategy_name: short prefix for this family's variant names in
            the output message (e.g. "mac", "donchian", "turtle").
        variants: variant name -> params, passed through unchanged to
            `compute_variant_signal` for that variant.
        compute_variant_signal: the strategy-specific per-ticker signal
            function -- see module docstring's 3-part contract.
    """

    accepts_context = _accepts_context(compute_variant_signal)

    def signal_computer(msg: Dict[str, Any]):
        """Worker body: (message) -> [(message, outport_name), ...]."""
        history = msg.get("history", {}) or {}
        context = msg.get("context") or {}
        market_return_by_date = context.get("market_return_by_date", {}) or {}
        context_per_ticker = context.get("per_ticker", {}) or {}
        series: Dict[str, dict] = {}
        ticker_volatility: Dict[str, float] = {}
        variant_names = [f"{strategy_name}_{v}" for v in variants]

        for ticker, bars in history.items():
            # Skip a ticker with no usable closing prices rather than
            # crashing the whole batch over one bad ticker.
            usable_bars = [b for b in bars if b.get("close") is not None]
            if len(usable_bars) < 2:
                continue

            closes = [b["close"] for b in usable_bars]
            dates = [b["date"] for b in usable_bars]
            returns = _daily_returns(closes)

            # Per-ticker cross-sectional context, aligned to THIS ticker's
            # usable bars by date so signal[t] and context[t] index the same
            # day. Built only for strategies that opted in; MARKET_CONTEXT
            # upstream computes the values causally.
            ticker_context: Optional[Dict[str, Any]] = None
            if accepts_context and context:
                tp = context_per_ticker.get(ticker, {})
                rank_by_date = tp.get("rs_rank_by_date", {})
                pct_by_date = tp.get("rs_percentile_by_date", {})
                rel_by_date = tp.get("rel_strength_by_date", {})
                ticker_context = {
                    "market_returns": [market_return_by_date.get(d) for d in dates],
                    "rs_rank":        [rank_by_date.get(d) for d in dates],
                    "rs_percentile":  [pct_by_date.get(d) for d in dates],
                    "rel_strength":   [rel_by_date.get(d) for d in dates],
                    "n_tickers":      context.get("n_tickers"),
                    "lookback":       context.get("lookback"),
                }

            signals: Dict[str, List[float]] = {}
            for variant_name, params in variants.items():
                if accepts_context:
                    sig = compute_variant_signal(usable_bars, params, ticker_context)
                else:
                    sig = compute_variant_signal(usable_bars, params)
                signals[f"{strategy_name}_{variant_name}"] = sig

            series[ticker] = {
                "dates": dates,
                "returns": returns,
                "signals": signals,
            }
            ticker_volatility[ticker] = _annualized_volatility(returns)

        out_msg = {
            "type":              "trend_signals",
            "tickers":           list(series.keys()),
            "variants":          variant_names,
            "series":            series,
            "ticker_volatility": ticker_volatility,
        }
        return [(out_msg, "out")]

    return signal_computer
