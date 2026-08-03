# dissyslab/gallery/apps/mac_speed_suite/draft_workers/signal_computer.py

"""
SIGNAL_COMPUTER -- Phase 2 draft worker body (NOT yet wired into any
office.md, NOT yet approved). Part of the "MAC speed suite" demo
office: one source -> SIGNAL_COMPUTER -> five concurrent BACKTESTER
workers -> JOIN -> EVALUATOR -> REPORT.

What this worker does, in plain terms
======================================

Man AHL's "MAC" (moving-average crossover) model compares a FAST
rolling average of a stock's price to a SLOW rolling average. When
the fast one is above the slow one, that means the price has recently
been doing noticeably better than its longer-term normal -- treat
that as "trend is up, bet the price keeps rising." When fast dips
below slow, treat that as "trend is down, bet the price falls."
Man AHL does not run just one such comparison -- they run a *suite*
of five, at different speeds (fast through slow), chosen so the five
are only weakly correlated with each other.

This worker computes, for every stock and every one of the five
speeds, that day-by-day up/down bet (the "signal"). It does NOT
compute whether any bet made money -- that is BACKTESTER's job, one
BACKTESTER per speed, run concurrently. Splitting the work this way
means the expensive part shared by all five speeds (turning a price
series into moving averages and returns) happens once here, rather
than being recomputed five times downstream.

Input message shape (from the `stock_history` / `synthetic_stock_history`
registered sources):
    {
        "type":    "stock_history",
        "tickers": ["AAPL", "MSFT", ...],
        "history": {
            "AAPL": [{"date": "2024-01-02", "open": ..., "high": ...,
                      "low": ..., "close": ..., "volume": ...}, ...],
            ...
        },
        ...
    }

Output message shape:
    {
        "type":    "mac_signals",
        "tickers": ["AAPL", "MSFT", ...],
        "speeds":  ["fast", "med_fast", "med", "med_slow", "slow"],
        "series": {
            "AAPL": {
                "dates":   ["2024-01-02", "2024-01-03", ...],
                "returns": [None, 0.0031, -0.0012, ...],
                "signals": {
                    "fast":     [1, 1, -1, ...],
                    "med_fast": [1, 1, 1, ...],
                    ...
                },
            },
            ...
        },
        "ticker_volatility": {"AAPL": 0.183, "MSFT": 0.201, ...},
    }

`returns[t]` is the stock's own day-over-day price return on day t
(``None`` on day 0, since there is no prior day to compare to).
`signals[speed][t]` is the crossover bet *decided using prices known
by the close of day t* -- see the "no lookahead" note in
``backtester.py`` for why that one-day offset matters and how it's
handled downstream, not here. `ticker_volatility[ticker]` is that
stock's own annualized volatility of its raw price returns (not any
one speed's strategy returns) -- used downstream by EVALUATOR for
inverse-volatility portfolio weighting.

Speed parameters
================

Man AHL has not published their exact fast/slow day-counts; the
five speeds below are a standard doubling-ladder stand-in (each
speed's pair roughly double the previous one's), the same convention
commonly used in public replications of multi-speed MAC systems.
Swap these for Man's real numbers if/when we ever get them; nothing
else about this worker's logic depends on the specific values.
"""

from typing import Any, Dict, List, Optional


# (fast_span, slow_span) in trading days, for each of Man AHL's five
# described speeds (fast through slow). "Span" follows the common
# exponentially-weighted-average convention: alpha = 2 / (span + 1).
MAC_SPEEDS: Dict[str, tuple] = {
    "fast":     (2, 8),
    "med_fast": (4, 16),
    "med":      (8, 32),
    "med_slow": (16, 64),
    "slow":     (32, 128),
}


def _ewma(prices: List[float], span: int) -> List[float]:
    """Exponentially weighted moving average of `prices`.

    Uses the common ``alpha = 2 / (span + 1)`` convention (matches
    pandas' ``.ewm(span=...)``). Seeded with the first price so the
    series starts immediately -- no NaN warm-up period to explain to
    a first-time reader.
    """
    alpha = 2.0 / (span + 1.0)
    out = [prices[0]]
    for p in prices[1:]:
        out.append(alpha * p + (1.0 - alpha) * out[-1])
    return out


def _daily_returns(prices: List[float]) -> List[Optional[float]]:
    """Day-over-day simple returns. Day 0 has no prior day -> None."""
    returns: List[Optional[float]] = [None]
    for prev, cur in zip(prices, prices[1:]):
        returns.append((cur - prev) / prev if prev else None)
    return returns


TRADING_DAYS_PER_YEAR = 252.0


def _annualized_volatility(returns: List[Optional[float]]) -> float:
    """Sample std of the stock's own *raw price* returns, annualized.

    This is a property of the stock itself -- not of any one MAC
    speed's strategy returns -- so it's computed once, here, rather
    than separately inside each of the five BACKTESTER instances.
    EVALUATOR uses it later for inverse-volatility portfolio weighting
    (see evaluator.py): a stock that bounces around twice as much gets
    half the portfolio weight, so every stock contributes roughly
    equal *risk* rather than equal share count.
    """
    values = [r for r in returns if r is not None]
    n = len(values)
    if n < 2:
        return 0.0
    mean = sum(values) / n
    variance = sum((r - mean) ** 2 for r in values) / (n - 1)
    return (variance ** 0.5) * (TRADING_DAYS_PER_YEAR ** 0.5)


def signal_computer(msg: Dict[str, Any]):
    """
    Worker body: (message) -> [(message, outport_name), ...].

    Matches the shape every DisSysLab worker function uses (see
    ``dissyslab.office.library.nl_role``'s ``role_fn`` for the same
    pattern) -- a list of (outgoing message, destination outport)
    pairs, here always exactly one pair on the single outport "out".
    """
    history = msg.get("history", {}) or {}
    series: Dict[str, dict] = {}
    ticker_volatility: Dict[str, float] = {}

    for ticker, bars in history.items():
        # Skip a ticker with no usable closing prices (e.g. it landed
        # in stock_history's own `errors` instead of `history`, or a
        # bar is missing `close` for some other reason) rather than
        # crashing the whole batch over one bad ticker.
        closes = [b["close"] for b in bars if b.get("close") is not None]
        dates = [b["date"] for b in bars if b.get("close") is not None]
        if len(closes) < 2:
            continue

        returns = _daily_returns(closes)
        signals = {}
        for speed_name, (fast_span, slow_span) in MAC_SPEEDS.items():
            fast_ewma = _ewma(closes, fast_span)
            slow_ewma = _ewma(closes, slow_span)
            signals[speed_name] = [
                1 if f > s else -1
                for f, s in zip(fast_ewma, slow_ewma)
            ]

        series[ticker] = {
            "dates": dates,
            "returns": returns,
            "signals": signals,
        }
        ticker_volatility[ticker] = _annualized_volatility(returns)

    out_msg = {
        "type":              "mac_signals",
        "tickers":           list(series.keys()),
        "speeds":            list(MAC_SPEEDS.keys()),
        "series":            series,
        # Each ticker's own raw-price volatility, computed once here
        # rather than five times (once per speed) downstream. Passed
        # through BACKTESTER unchanged into every one of its five
        # messages -- see backtester.py's docstring for why an
        # identical value across all five is safe for JOIN's merge,
        # unlike the speed-specific fields.
        "ticker_volatility": ticker_volatility,
    }
    return [(out_msg, "out")]
