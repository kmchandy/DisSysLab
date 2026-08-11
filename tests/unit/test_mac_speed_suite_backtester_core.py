# tests/unit/test_mac_speed_suite_backtester_core.py
"""
Tier-3 invariant tests for BACKTESTER (`_backtester_core.make_backtester`)
-- shared machinery every mac_speed_suite strategy relies on unchanged.
The contract's whole "extend without touching shared files" promise
depends on this machinery being correct once, for every strategy, not
re-verified per strategy -- so unlike check_no_lookahead.py (which runs
per new strategy), these tests live in DisSysLab's own permanent test
suite and run once for everyone.

The specific bug these guard against, distinct from a strategy's own
no-lookahead property: even a perfectly causal signal can be misused by
the *accounting* step if it's multiplied against the wrong day's
return. This is a second place a lookahead-shaped bug can hide that
check_no_lookahead.py cannot see, because that check only looks at the
signal function, never at BACKTESTER.
"""

from __future__ import annotations

from dissyslab.gallery.apps.mac_speed_suite.roles._backtester_core import make_backtester


def _run(speed_name: str, series: dict, ticker_volatility: dict | None = None) -> dict:
    backtester = make_backtester(speed_name, cost_bps=0.0)  # test lag accounting, not costs
    msg = {"ticker_volatility": ticker_volatility or {}, "series": series}
    out_msgs = backtester(msg)
    assert len(out_msgs) == 1
    out_msg, port = out_msgs[0]
    assert port == "out"
    return out_msg


def test_day_zero_has_no_prior_signal_so_return_is_zero():
    """No day -1 signal exists, so day 0's strategy return must be
    exactly 0.0 by definition, regardless of what day 0's own signal or
    return happen to be."""
    out = _run("fast", {"AAPL": {"returns": [None, 0.05], "signals": {"fast": [1.0, 1.0]}}})
    assert out["fast"]["per_ticker_returns"]["AAPL"][0] == 0.0


def test_strategy_return_uses_prior_day_signal_not_same_day():
    """The core invariant: strat_return[t] = signal[t-1] * return[t].
    Chosen so a same-day (buggy) computation would give a different,
    wrong-signed answer -- signal flips from +1 to -1 specifically so
    lagged vs. same-day disagree, not just differ in magnitude."""
    out = _run("fast", {
        "AAPL": {
            "returns": [None, 0.10, 0.10],
            "signals": {"fast": [1.0, -1.0, -1.0]},
        },
    })
    strat = out["fast"]["per_ticker_returns"]["AAPL"]
    # day 1: prior_signal = signal[0] = 1.0  -> 1.0 * 0.10 = 0.10
    #   (a same-day bug would compute signal[1] * 0.10 = -1.0 * 0.10 = -0.10)
    # day 2: prior_signal = signal[1] = -1.0 -> -1.0 * 0.10 = -0.10
    assert strat == [0.0, 0.10, -0.10]


def test_missing_return_gives_zero_not_a_crash_or_none():
    """A day with no return (e.g. a data gap) must contribute 0.0 to
    the strategy's return series, not propagate None or raise."""
    out = _run("fast", {
        "AAPL": {"returns": [None, None, 0.02], "signals": {"fast": [1.0, 1.0, 1.0]}},
    })
    assert out["fast"]["per_ticker_returns"]["AAPL"] == [0.0, 0.0, 0.02]


def test_ticker_without_this_speed_signal_is_skipped_not_crashed():
    """A ticker whose series doesn't have this BACKTESTER's speed_name
    (e.g. misaligned data) is skipped -- one bad ticker must not take
    down the whole backtest."""
    out = _run("fast", {
        "AAPL": {"returns": [None, 0.01], "signals": {"fast": [1.0, 1.0]}},
        "MSFT": {"returns": [None, 0.01], "signals": {"slow": [1.0, 1.0]}},  # no "fast"
    })
    assert "AAPL" in out["fast"]["per_ticker_returns"]
    assert "MSFT" not in out["fast"]["per_ticker_returns"]


def test_each_backtester_only_reads_its_own_speed():
    """BT_FAST must never read BT_SLOW's signal column, even when both
    are present in the same message -- this is what lets every speed's
    BACKTESTER run concurrently with zero coordination."""
    out = _run("fast", {
        "AAPL": {
            "returns": [None, 0.10],
            "signals": {"fast": [1.0, 1.0], "slow": [-1.0, -1.0]},
        },
    })
    # If this BACKTESTER accidentally read "slow", day 1 would be -0.10.
    assert out["fast"]["per_ticker_returns"]["AAPL"][1] == 0.10


def test_ticker_volatility_passed_through_unchanged():
    """ticker_volatility is a property of the stock (computed once
    upstream), not of any one speed -- BACKTESTER must forward it
    unmodified so EVALUATOR's inverse-volatility weighting is correct
    regardless of which speed produced the message."""
    out = _run(
        "fast",
        {"AAPL": {"returns": [None, 0.01], "signals": {"fast": [1.0, 1.0]}}},
        ticker_volatility={"AAPL": 0.234},
    )
    assert out["ticker_volatility"] == {"AAPL": 0.234}


def test_output_nested_under_speed_name_not_top_level():
    """Regression guard for the JOIN merge-collision bug documented in
    _backtester_core.py's own docstring: per_ticker_returns must be
    nested under this BACKTESTER's own speed_name key, not placed at
    the message's top level, or JOIN's synchronizer would raise a
    field-collision error the moment two speeds' messages merge."""
    out = _run("med_fast", {"AAPL": {"returns": [None, 0.01], "signals": {"med_fast": [1.0, 1.0]}}})
    assert "per_ticker_returns" not in out  # not at top level
    assert "per_ticker_returns" in out["med_fast"]  # nested correctly
