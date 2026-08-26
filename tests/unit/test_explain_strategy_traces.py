"""Every strategy the office ranks can show its working.

`explain_strategy.py` covered Donchian and MAC. Turtle and RS did not
have a tracer at all, so *"show me the working for Turtle"* -- the
strategy the tester was actually working on, and the one he had built
his own spreadsheet for -- answered with a list of the two strategies
that were supported.

The guard that matters is `_agree`: a tracer recomputes the
intermediates and then asserts they imply the signal the *strategy
module* produced. Two expressions of one rule, and the export refuses
rather than showing working that does not match the code it claims to
explain. These tests exercise that guard on real bars.

They do not check the Excel formulas. Those were verified by
recalculating both workbooks in LibreOffice and reading the match
columns -- 43 and 84 rows, all "ok" -- which found a real defect first
time: N's warm-up is a plain mean of the true ranges so far, not the
Wilder recurrence, and writing the recurrence for those rows made
every later row disagree, because a recurrence carries its seed
forward for ever.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
APP = REPO_ROOT / "dissyslab" / "gallery" / "apps" / "mac_speed_suite"


@pytest.fixture(scope="module")
def explain():
    sys.path.insert(0, str(APP / "roles"))
    spec = importlib.util.spec_from_file_location(
        "explain_strategy", APP / "explain_strategy.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_every_shipped_strategy_family_has_a_tracer(explain):
    """The check that keeps this from happening again. A strategy the
    office ranks but cannot explain is one a tester is told to trust on
    our word."""
    from dissyslab.office.library import load_roles_dir

    signal_roles = {
        name.replace("_signal", "").replace("rs_trend", "rs")
        for name in load_roles_dir(APP / "roles")
        if name.endswith("_signal") or name == "rs_trend"
    }
    missing = signal_roles - set(explain.TRACERS)
    assert not missing, (
        f"{sorted(missing)} produce signals the office ranks, and "
        f"`explain_strategy.py` cannot show their working. Someone "
        f"asking 'is this the strategy I meant?' gets no answer for "
        f"them."
    )


@pytest.mark.parametrize("variant", ["s1", "s2"])
def test_the_turtle_trace_agrees_with_the_turtle_role(explain, variant):
    """`_agree` raises SystemExit on any disagreement, so reaching the
    end is the assertion. Turtle is the hard case: its position is a
    state machine -- units on, where the last one was added, where the
    stop is -- so the tracer has to reproduce the path, not a
    formula."""
    bars = explain._synthetic_bars(200)
    trace = explain.turtle_trace(bars, variant)
    assert trace.name == f"turtle_{variant}"
    assert [r["signal"] for r in trace.rows] == list(
        explain._turtle_compute_variant_signal(
            bars, explain.TURTLE_VARIANTS[variant]
        )
    )


def test_the_turtle_trace_actually_trades(explain):
    """A trace of a strategy that never opens a position demonstrates
    nothing, and would pass the agreement check trivially."""
    trace = explain.turtle_trace(explain._synthetic_bars(200), "s1")
    signals = {r["signal"] for r in trace.rows}
    assert len(signals) > 1, "the turtle trace never leaves flat"
    assert any(r["units"] != 0 for r in trace.rows)


def test_turtle_shows_no_formula_for_the_path_dependent_columns(explain):
    """Deliberate, and the reason it is worth a test: units, stop and
    signal depend on the whole path. A cell formula pretending to
    compute them from one row would misrepresent the strategy to the
    one person reading the sheet to find out how it works."""
    derived = explain._DERIVED["turtle"]
    for name in ("units", "stop", "signal"):
        assert name not in derived
    for name in ("tr", "N", "entry_high", "entry_low"):
        assert name in derived


@pytest.mark.parametrize("variant", ["fast", "slow"])
def test_the_rs_trace_agrees_with_the_rs_role(explain, variant):
    """RS is the case where the working is not all on one sheet: the
    strength half is computed from the *other* stocks in the basket.
    The tracer gets that number from MARKET_CONTEXT's own code rather
    than reimplementing it -- two copies of that arithmetic is how the
    four-dots path bug happened."""
    peers = {
        name: explain._synthetic_bars(200, seed=i)
        for i, name in enumerate(explain.DEFAULT_PEERS)
    }
    # The strongest of the basket, so that the strength half can be
    # satisfied at all. The weakest stock is flat on every row, which
    # is correct behaviour and a useless demonstration.
    bars = peers[explain.DEFAULT_PEERS[-1]]
    trace = explain.rs_trace(bars, variant, peers=peers)
    assert trace.name == f"rs_{variant}"
    assert {r["signal"] for r in trace.rows} == {0.0, 1.0}, (
        "the rs trace never takes a position, so it demonstrates nothing"
    )


def test_rs_without_peers_is_flat_and_says_so(explain):
    """The role behaves this way too -- no MARKET_CONTEXT upstream
    means no relative strength, so it holds nothing. The trace must
    agree with the role rather than inventing a cross-section."""
    bars = explain._synthetic_bars(200)
    trace = explain.rs_trace(bars, "fast", peers=None)
    assert {r["signal"] for r in trace.rows} == {0.0}
    assert any("no peer data" in r["why"] for r in trace.rows)


def test_a_synthetic_basket_is_not_five_identical_stocks(explain):
    """RS ranks a stock against its peers. Five identical peers rank by
    tie-break, and a sheet built on that would teach a reader something
    untrue about what the strategy does."""
    a = explain._synthetic_bars(60, seed=0)
    b = explain._synthetic_bars(60, seed=3)
    assert [x["close"] for x in a] != [x["close"] for x in b]


def test_a_tracer_that_disagrees_refuses_to_write(explain):
    """The guard itself, exercised. It has to fail loudly: working that
    silently disagrees with the code it explains is worse than no
    working at all, because someone will read it and believe it."""
    rows = [{"signal": 1.0}, {"signal": -1.0}]
    with pytest.raises(SystemExit) as exc:
        explain._agree(rows, [1.0, 1.0], "made_up")
    assert "disagrees with the strategy at bar 1" in str(exc.value)
