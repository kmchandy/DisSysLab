# dissyslab/gallery/apps/mac_speed_suite/draft_workers/backtester.py

"""
BACKTESTER -- Phase 2 draft worker body (NOT yet wired into any
office.md, NOT yet approved). Five of these run concurrently, one per
MAC speed, downstream of SIGNAL_COMPUTER in the "MAC speed suite"
demo office.

What this worker does, in plain terms
======================================

SIGNAL_COMPUTER already decided, for every stock and every speed,
each day's bet: "price goes up" or "price goes down." A BACKTESTER's
job is to answer: if you had actually placed that one speed's bets,
day after day, across every stock -- what would have happened? Did
the price move the way the bet predicted (a gain) or the opposite way
(a loss), and by how much? Add all of that up across every stock and
every day, and you get a day-by-day story of what this one speed's
trading rule would have earned, had it really been followed.

Each BACKTESTER is built for exactly one speed (via
``make_backtester(speed_name)``) and only ever reads that speed's
column out of SIGNAL_COMPUTER's message -- it never looks at another
speed's bets. That's what lets all five run at the same time with no
coordination needed between them: they're reading the same upstream
message, but each is only looking at its own slice of it.

The no-lookahead rule (the one classic backtesting bug this avoids)
=====================================================================

A day's crossover bet can only be *computed* using prices known by
that day's close -- so it can't possibly be the bet that was already
"in place" during that same day; it can only govern the *next* day.
Concretely: the bet decided at the close of day t (``signal[t]``)
determines whether you're long or short *during day t+1*, and so it
gets multiplied against day (t+1)'s return, never day t's own return.
Multiplying a day's bet against that same day's return would silently
mean "trading on tomorrow's closing price before today ends" --
inflating the backtest with information that wasn't actually
available yet. This module lags the signal by exactly one day to
avoid that.

Input message shape (SIGNAL_COMPUTER's output):
    {
        "type":   "mac_signals",
        "series": {
            "AAPL": {
                "dates":   [...],
                "returns": [None, 0.0031, ...],
                "signals": {"fast": [...], "med_fast": [...], ...},
            },
            ...
        },
        "ticker_volatility": {"AAPL": 0.183, ...},
        ...
    }

Output message shape (one BACKTESTER's result, for its one speed):
    {
        "type": "mac_backtest",
        "ticker_volatility": {"AAPL": 0.183, ...},   # passed through
                                                       # unchanged -- see below
        "fast": {                                     # this BACKTESTER's
            "per_ticker_returns": {"AAPL": [...], ...},  # own speed_name,
        },                                             # nested -- see below
    }

Deliberately no portfolio-level number here: BACKTESTER's job stops at
"what happened to each individual stock." Turning many stocks into one
portfolio return -- equal-weighted, inverse-volatility-weighted (the
default EVALUATOR uses), or some other scheme -- is a real design
choice, and it belongs entirely to EVALUATOR; BACKTESTER shouldn't be
the place quietly deciding that. `ticker_volatility` (each stock's own
raw-price volatility, computed once in SIGNAL_COMPUTER) is forwarded
unchanged so EVALUATOR has what it needs for that weighting.

Why `ticker_volatility` and `per_ticker_returns` are nested/placed the
way they are, rather than however seemed convenient (a bug caught
while designing EVALUATOR, before anything was ever run):
caught while designing EVALUATOR, before anything was ever run):
JOIN is a plain `synchronizer_role`, which dict-merges its five
inports' messages by flatly copying each message's top-level keys
into one combined dict -- it does NOT namespace by which inport a
message arrived on. An earlier draft of this module put `speed`,
`per_ticker_returns`, and `portfolio_returns` directly at the top
level of every BACKTESTER's message. All five BACKTESTERs use those
exact same key names with *different* values (different speed,
different numbers) -- so the moment JOIN tried to merge them, its own
built-in conflict check (real, and correct) would raise an error
naming the collision, e.g. "inport 'med_fast' supplied field 'speed'
with a different value than an earlier inport this round already
set." Nesting each BACKTESTER's result under its own `speed_name` key
gives all five messages disjoint top-level keys, except two keys every
BACKTESTER deliberately shares: `"type"` and `"ticker_volatility"`.
Sharing them is safe -- and different from the `speed`/`returns` bug
above -- specifically because all five BACKTESTERs report the exact
same value for both (the type tag never varies; `ticker_volatility`
is a per-stock property forwarded unchanged from SIGNAL_COMPUTER, not
computed separately per speed), and JOIN's conflict check only ever
fires on a *mismatched* value for a shared key, not on the sharing
itself. So JOIN's merge produces exactly
    {
        "type": "mac_backtest",
        "ticker_volatility": {"AAPL": 0.183, ...},
        "fast": {...}, "med_fast": {...}, "med": {...},
        "med_slow": {...}, "slow": {...},
    }
which is also the exact shape EVALUATOR wants to read.
"""

from typing import Any, Callable, Dict


def make_backtester(speed_name: str) -> Callable[[Dict[str, Any]], list]:
    """
    Build a BACKTESTER worker body for exactly one MAC speed.

    Called once per speed when the five BACKTESTER agents are set up
    (e.g. ``make_backtester("fast")``, ``make_backtester("slow")``,
    ...) -- each resulting function only ever reads its own
    ``speed_name``'s signal column, which is what lets all five run
    concurrently with no shared state between them.
    """

    def backtester(msg: Dict[str, Any]):
        """Worker body: (message) -> [(message, outport_name), ...]."""
        series = msg.get("series", {}) or {}
        per_ticker_returns: Dict[str, list] = {}

        for ticker, data in series.items():
            returns = data.get("returns", [])
            signal = data.get("signals", {}).get(speed_name)
            if not signal or len(signal) != len(returns):
                # This ticker doesn't have this speed's signal (or the
                # two series are misaligned) -- skip rather than crash
                # the whole backtest over one ticker.
                continue

            # Day 0: no prior-day signal exists yet, so no position is
            # held and the strategy return is 0 by definition.
            strat_returns = [0.0]
            for t in range(1, len(returns)):
                prior_signal = signal[t - 1]   # decided at close of day t-1
                today_return = returns[t]      # day t's actual return
                if today_return is None:
                    strat_returns.append(0.0)
                else:
                    strat_returns.append(prior_signal * today_return)

            per_ticker_returns[ticker] = strat_returns

        # No portfolio-level combining here on purpose: BACKTESTER's
        # job stops at "what happened to each stock." How the stocks
        # get combined into one portfolio number -- equal-weighted,
        # inverse-volatility-weighted, or something else -- is a real
        # design choice (see evaluator.py's inverse-volatility
        # weighting), and belongs to EVALUATOR, the one place that
        # decides what "portfolio" means. `ticker_volatility` is
        # passed through unchanged from SIGNAL_COMPUTER's message
        # (identical across all five BACKTESTER instances, since it's
        # a property of the stock, not the speed) so EVALUATOR has
        # what it needs for that weighting without recomputing it.
        out_msg = {
            "type": "mac_backtest",
            "ticker_volatility": msg.get("ticker_volatility", {}),
            speed_name: {
                "per_ticker_returns": per_ticker_returns,
            },
        }
        return [(out_msg, "out")]

    return backtester
