"""
---
emits: the daily signals of every mac variant, for one span
kind: author
in: span, history
out: span, type, tickers, variants, series, ticker_volatility, _wf_tag
---
"""
# dissyslab/gallery/mac_speed_suite/roles/mac_signal.py

"""
MAC (moving-average crossover) signal computer -- Man AHL-style, five
concurrent speeds. Refactored onto the shared `make_signal_computer`
factory (see _signal_common.py); the actual crossover math is unchanged
from the original single-strategy version of this office.

Compares a FAST rolling average of a stock's price to a SLOW rolling
average. Fast above slow -> "trend is up, bet the price keeps rising."
Fast below slow -> "trend is down, bet the price falls." Man AHL runs a
*suite* of five such comparisons at different speeds, chosen so the
five are only weakly correlated with each other.

Speed parameters: Man AHL has not published their exact fast/slow
day-counts; the five speeds below are a standard doubling-ladder
stand-in (each pair roughly double the previous one's), the same
convention commonly used in public replications of multi-speed MAC
systems -- not Man's own disclosed numbers.
"""

from typing import List, Tuple

from _signal_common import make_signal_computer


# (fast_span, slow_span) in trading days, for each of Man AHL's five
# described speeds (fast through slow). "Span" follows the common
# exponentially-weighted-average convention: alpha = 2 / (span + 1).
MAC_VARIANTS = {
    "fast":     (2, 8),
    "med_fast": (4, 16),
    "med":      (8, 32),
    "med_slow": (16, 64),
    "slow":     (32, 128),
}


def _ewma(prices: List[float], span: int) -> List[float]:
    """Exponentially weighted moving average. Seeded with the first
    price so the series starts immediately -- no NaN warm-up period."""
    alpha = 2.0 / (span + 1.0)
    out = [prices[0]]
    for p in prices[1:]:
        out.append(alpha * p + (1.0 - alpha) * out[-1])
    return out


def _mac_compute_variant_signal(bars: List[dict], params: Tuple[int, int]) -> List[float]:
    """One MAC speed's day-by-day bet: +1.0 (fast above slow) or
    -1.0 (fast below slow). No lookahead: `_ewma` at day t only uses
    prices[0..t]."""
    fast_span, slow_span = params
    closes = [b["close"] for b in bars]
    fast_ewma = _ewma(closes, fast_span)
    slow_ewma = _ewma(closes, slow_span)
    return [1.0 if f > s else -1.0 for f, s in zip(fast_ewma, slow_ewma)]


# ── The role (DisSysLab 2.0) ──────────────────────────────────────────────


class MacSignal:
    """One span of price history -> the signals of every mac variant.

    ``checks="on"`` runs the strategy contract (no lookahead, deterministic,
    finite) the first time each variant is used (``_signal_common``).
    """

    def __init__(self, checks="on"):
        self.compute = make_signal_computer("mac", MAC_VARIANTS, _mac_compute_variant_signal, checks=checks)

    def __call__(self, item):
        ((out, _port),) = self.compute(item)
        return [{**out, "span": item["span"]}]
