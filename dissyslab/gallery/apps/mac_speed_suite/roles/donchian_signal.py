# dissyslab/gallery/apps/mac_speed_suite/roles/donchian_signal.py

"""
Donchian channel breakout signal computer.

The classic Donchian channel rule: over a rolling window of N prior
days, track the highest high and the lowest low. Go long when today's
close breaks above the highest high of the *prior* N days; go short
when it breaks below the lowest low of the prior N days. Otherwise,
hold whatever position you already had -- a pure breakout system is
always in the market, long or short, reversing only on the opposite
breakout (the standard "always in" convention used in most public
replications of Donchian/Turtle-style systems).

Two variants are provided, using the same two window lengths Richard
Dennis's Turtle system made famous (20 and 55 trading days) -- but
unlike Turtle (see turtle_signal.py), this is the *plain* channel
system: no ATR-based stop-loss, no pyramiding, always fully long or
fully short (+1.0 / -1.0). Turtle is Donchian's breakout rule plus
volatility-based position sizing and risk management on top; keeping
plain Donchian as its own strategy family lets EVALUATOR compare "the
breakout signal alone" against "the breakout signal with Turtle's
sizing/exit discipline" directly.

No lookahead: the breakout check at day t only ever looks at
highs/lows[t-window : t] -- yesterday and earlier, never today's own
high/low used to decide today's signal.
"""

import os
import sys
from typing import List

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _signal_common import make_signal_computer  # noqa: E402

from dissyslab.blocks.role import Role
from dissyslab.office.library import AgentRoleEntry

# variant name -> breakout window, in trading days.
DONCHIAN_VARIANTS = {
    "20": 20,
    "55": 55,
}


def _donchian_compute_variant_signal(bars: List[dict], window: int) -> List[float]:
    highs = [b["high"] for b in bars]
    lows = [b["low"] for b in bars]
    closes = [b["close"] for b in bars]
    n = len(bars)

    signal = [0.0] * n
    position = 0.0  # 0.0 until the first breakout ever occurs
    for t in range(n):
        if t >= window:
            prior_high = max(highs[t - window:t])
            prior_low = min(lows[t - window:t])
            if closes[t] > prior_high:
                position = 1.0
            elif closes[t] < prior_low:
                position = -1.0
            # else: no breakout today -- hold the existing position.
        signal[t] = position
    return signal


role = AgentRoleEntry(
    name="donchian_signal",
    in_ports=("in_",),
    out_ports=("out",),
    factory=lambda: Role(
        fn=make_signal_computer(
            "donchian", DONCHIAN_VARIANTS, _donchian_compute_variant_signal
        ),
        statuses=["out"],
    ),
)
