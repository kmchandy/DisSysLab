# dissyslab/gallery/apps/mac_speed_suite/roles/turtle_signal.py

"""
Turtle system signal computer -- the Richard Dennis / Richard Dennis's
"Turtles" breakout system, simplified.

Two systems, matching the Turtles' own published parameters:
    - System 1: enter on a 20-day breakout, exit on a 10-day
      opposite-direction breakout.
    - System 2: enter on a 55-day breakout, exit on a 20-day
      opposite-direction breakout.

Unlike plain Donchian (donchian_signal.py), Turtle adds the two things
that made it a *risk-managed* system rather than a bare breakout rule:

  1. Volatility-scaled position sizing via "N" (Average True Range,
     Wilder-smoothed over `atr_period` days) -- a stock that's moving
     twice as much per day gets a proportionally tighter stop, and
     pyramided units are added at N/2-price intervals rather than
     fixed dollar/percentage intervals, so sizing adapts to each
     stock's own recent volatility.
  2. Pyramiding up to `max_units` units (default 4, matching the
     Turtles' own convention) as a winning trade extends, each unit a
     step of 1/max_units in the returned signal -- and a hard stop-loss
     at `stop_atr_mult` x N (default 2N) from the most recent unit's
     entry price.

The returned signal is therefore a continuous position size in
{-1.0, -0.75, ..., 0.75, 1.0} (four units, positive or negative), not
just +/-1.0 -- this is the strategy this office uses to exercise the
generalized "position size, not just direction" signal contract (see
_signal_common.py's docstring). BACKTESTER needs no changes to handle
it: its `prior_signal * today_return` math already works for any
continuous value.

Deliberate simplifications (documented, not hidden -- same spirit as
MAC's speed-ladder stand-in): no "skip this breakout if the last trade
in this direction was a winner" filter (a real but often-omitted
refinement in public replications); position sizing here is a fraction
of one strategy-level "unit" (not real share counts, dollar risk, or
per-instrument volatility-adjusted contract counts, since this office
works in returns, not dollars); no cross-instrument correlation or
portfolio-heat cap (handled at the portfolio level by EVALUATOR's
inverse-volatility weighting instead, not here).

No lookahead: entry/exit breakout levels at day t use only
highs/lows[t-period : t]; N (ATR) at day t uses only bars[0..t]
(today's own high/low/prior close, all known by today's close, same as
MAC using today's own close and Donchian using today's own high/low).
"""

import os
import sys
from typing import Any, Dict, List

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _signal_common import make_signal_computer  # noqa: E402

from dissyslab.blocks.role import Role
from dissyslab.office.library import AgentRoleEntry

TURTLE_VARIANTS: Dict[str, Dict[str, Any]] = {
    "s1": {"entry": 20, "exit": 10, "atr_period": 20, "max_units": 4, "stop_atr_mult": 2.0},
    "s2": {"entry": 55, "exit": 20, "atr_period": 20, "max_units": 4, "stop_atr_mult": 2.0},
}


def _true_range(bars: List[dict], t: int) -> float:
    high = bars[t]["high"]
    low = bars[t]["low"]
    prev_close = bars[t - 1]["close"] if t > 0 else bars[t]["close"]
    return max(high - low, abs(high - prev_close), abs(low - prev_close))


def _atr_series(bars: List[dict], period: int) -> List[float]:
    """Wilder-smoothed Average True Range. Simple mean during the
    warm-up (t < period) so there's no NaN warm-up gap to explain."""
    n = len(bars)
    tr = [_true_range(bars, t) for t in range(n)]
    if n == 0:
        return []
    atr = [tr[0]]
    for t in range(1, n):
        if t < period:
            atr.append(sum(tr[: t + 1]) / (t + 1))
        else:
            atr.append((atr[-1] * (period - 1) + tr[t]) / period)
    return atr


def _turtle_compute_variant_signal(bars: List[dict], params: Dict[str, Any]) -> List[float]:
    entry_period = params["entry"]
    exit_period = params["exit"]
    atr_period = params["atr_period"]
    max_units = params["max_units"]
    stop_mult = params["stop_atr_mult"]
    unit_size = 1.0 / max_units

    highs = [b["high"] for b in bars]
    lows = [b["low"] for b in bars]
    closes = [b["close"] for b in bars]
    n = len(bars)
    atr = _atr_series(bars, atr_period)

    signal = [0.0] * n
    position_units = 0        # signed integer, -max_units .. +max_units
    entry_price = None        # price at which the most recent unit was added
    stop_price = None

    for t in range(n):
        price = closes[t]
        day_atr = atr[t] if atr[t] else 0.0

        prior_high = max(highs[t - entry_period:t]) if t >= entry_period else None
        prior_low = min(lows[t - entry_period:t]) if t >= entry_period else None
        exit_low = min(lows[t - exit_period:t]) if t >= exit_period else None
        exit_high = max(highs[t - exit_period:t]) if t >= exit_period else None

        if position_units == 0:
            # Flat -- look for a new breakout entry.
            if prior_high is not None and price > prior_high:
                position_units = 1
                entry_price = price
                stop_price = price - stop_mult * day_atr
            elif prior_low is not None and price < prior_low:
                position_units = -1
                entry_price = price
                stop_price = price + stop_mult * day_atr

        elif position_units > 0:
            # Long -- consider adding a unit (pyramiding), then check
            # for a stop-out or an opposite-direction exit breakout.
            if (
                position_units < max_units
                and entry_price is not None
                and day_atr > 0
                and price >= entry_price + 0.5 * day_atr
            ):
                position_units += 1
                entry_price = price
                stop_price = price - stop_mult * day_atr
            if (stop_price is not None and price <= stop_price) or (
                exit_low is not None and price < exit_low
            ):
                position_units = 0
                entry_price = None
                stop_price = None

        else:
            # Short -- symmetric to the long case.
            if (
                position_units > -max_units
                and entry_price is not None
                and day_atr > 0
                and price <= entry_price - 0.5 * day_atr
            ):
                position_units -= 1
                entry_price = price
                stop_price = price + stop_mult * day_atr
            if (stop_price is not None and price >= stop_price) or (
                exit_high is not None and price > exit_high
            ):
                position_units = 0
                entry_price = None
                stop_price = None

        signal[t] = position_units * unit_size

    return signal


role = AgentRoleEntry(
    name="turtle_signal",
    in_ports=("in_",),
    out_ports=("out",),
    factory=lambda: Role(
        fn=make_signal_computer("turtle", TURTLE_VARIANTS, _turtle_compute_variant_signal),
        statuses=["out"],
    ),
)
