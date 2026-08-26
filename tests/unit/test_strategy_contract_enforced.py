"""The look-ahead check is enforced, and the checker has been shown to fail.

Two separate claims, and the second is the one that was missing.

**Enforced.** The check existed and was invoked by a sentence in
`skills/backtest-strategy-builder/SKILL.md` telling an assistant to run
a script. That makes it a request to a language model: if the model did
not run it, nothing anywhere recorded the fact, and the office produced
a ranking that looked exactly like a checked one. It now runs inside
`make_signal_computer`, on each variant's first real message, so it
holds for strategies written after it and for assistants that never
read the skill.

**Shown to fail.** A checker nobody has watched fail is a checker
nobody should trust -- worse than none, because people stop looking.
Every check below is given a subject deliberately built to break it.

Why first use and not assembly: the look-ahead check needs data. It
recomputes the signal on truncated history and asserts day t's value
does not move when later bars are added, and at assembly no data has
flowed.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
ROLES = REPO_ROOT / "dissyslab" / "gallery" / "apps" / "mac_speed_suite" / "roles"
sys.path.insert(0, str(ROLES))

from _contract_checks import (  # noqa: E402
    check_deterministic,
    check_finite,
    check_no_lookahead,
)
from _signal_common import (  # noqa: E402
    StrategyContractError,
    _VERIFIED,
    make_signal_computer,
)


def _bars(n: int = 120) -> list[dict]:
    """A wobbling price series -- enough movement that a peeking
    strategy and an honest one actually disagree."""
    out, price = [], 100.0
    for i in range(n):
        price *= 1 + 0.01 * math.sin(i / 3.0) + 0.002 * math.cos(i / 7.0)
        out.append({
            "date": f"2020-01-{i + 1:03d}",
            "open": price, "high": price * 1.01,
            "low": price * 0.99, "close": price, "volume": 1000,
        })
    return out


# ── subjects built to fail ────────────────────────────────────────────


def _peeking(bars, _params):
    """Tomorrow's close decides today's position. This is the bug the
    whole apparatus exists for: it backtests beautifully and there is
    nothing in the output that looks wrong."""
    n = len(bars)
    return [
        1.0 if t + 1 < n and bars[t + 1]["close"] > bars[t]["close"] else -1.0
        for t in range(n)
    ]


def _honest(bars, _params):
    """Yesterday's move decides today. Uses only bars[0..t]."""
    return [
        1.0 if t > 0 and bars[t]["close"] > bars[t - 1]["close"] else -1.0
        for t in range(len(bars))
    ]


_counter = {"n": 0}


def _nondeterministic(bars, _params):
    _counter["n"] += 1
    return [float(_counter["n"] % 2)] * len(bars)


def _not_finite(bars, _params):
    return [float("nan")] * len(bars)


# ── the checkers fail on them ─────────────────────────────────────────


def test_the_lookahead_check_catches_a_strategy_that_peeks():
    """The assertion that licenses every other claim in this file. A
    check that has never been seen to fail is indistinguishable from a
    function that returns True."""
    result = check_no_lookahead(_peeking, None, _bars(), sample_every=1)
    assert not result["passed"]
    v = result["first_violation"]
    assert v["truncated_signal_value"] != v["full_signal_value"]


def test_the_lookahead_check_passes_an_honest_strategy():
    """The other half. A check that fails on everything is also
    useless, and is how a team learns to pass `checks='off'` by
    habit."""
    assert check_no_lookahead(_honest, None, _bars(), sample_every=1)["passed"]


def test_sampling_still_catches_it():
    """Enforcement samples every fifth day so that eleven variants cost
    seconds rather than half a minute. That is only sound because a
    strategy that peeks does so on essentially every bar -- the bug is
    a line of code, not an occasional event."""
    assert not check_no_lookahead(_peeking, None, _bars(), sample_every=5)["passed"]


def test_the_determinism_check_catches_a_changing_answer():
    _counter["n"] = 0
    assert not check_deterministic(_nondeterministic, None, _bars())["passed"]


def test_the_finiteness_check_catches_a_nan():
    assert not check_finite(_not_finite, None, _bars())["passed"]


def test_the_three_checks_pass_every_shipped_strategy():
    """If enforcement broke the offices we ship, that is worth knowing
    here rather than from a tester."""
    from donchian_signal import (
        DONCHIAN_VARIANTS, _donchian_compute_variant_signal,
    )
    from mac_signal import MAC_VARIANTS, _mac_compute_variant_signal
    from turtle_signal import TURTLE_VARIANTS, _turtle_compute_variant_signal

    bars = _bars(400)
    for fn, variants in (
        (_donchian_compute_variant_signal, DONCHIAN_VARIANTS),
        (_mac_compute_variant_signal, MAC_VARIANTS),
        (_turtle_compute_variant_signal, TURTLE_VARIANTS),
    ):
        for name, params in variants.items():
            assert check_no_lookahead(fn, params, bars, sample_every=5)["passed"], name
            assert check_deterministic(fn, params, bars)["passed"], name
            assert check_finite(fn, params, bars)["passed"], name


# ── enforcement, through the office's own path ────────────────────────


def _message(bars):
    return {"type": "stock_history", "tickers": ["AAA"], "history": {"AAA": bars}}


@pytest.fixture(autouse=True)
def _forget_what_was_verified():
    """The memo is process-wide and these tests reuse function names."""
    _VERIFIED.clear()
    yield
    _VERIFIED.clear()


def test_a_peeking_strategy_stops_the_office_on_its_first_message():
    """The whole point. Nobody asked for this check, no assistant chose
    to run it, and the strategy still does not get ranked."""
    computer = make_signal_computer("peek", {"v1": None}, _peeking)
    with pytest.raises(StrategyContractError) as exc:
        computer(_message(_bars()))

    text = str(exc.value)
    assert "peek_v1" in text
    assert "uses a later bar" in text
    # and it says how to proceed anyway, in the file rather than a flag
    assert "checks='off'" in text


def test_an_honest_strategy_is_unaffected():
    computer = make_signal_computer("fine", {"v1": None}, _honest)
    out = computer(_message(_bars()))
    assert out[0][1] == "out"
    assert "fine_v1" in out[0][0]["series"]["AAA"]["signals"]


def test_the_waiver_is_honoured():
    """`checks='off'` exists so that a false positive is a nuisance
    rather than a wall. It is written in office.md, where anyone
    reading the office can see it -- not passed as a flag that is
    invisible six weeks later."""
    computer = make_signal_computer("peek", {"v1": None}, _peeking, checks="off")
    out = computer(_message(_bars()))
    assert out[0][1] == "out"


def test_each_variant_is_checked_once_and_not_once_per_ticker():
    """Eleven backtesters share four signal functions and an office
    runs several tickers. Re-verifying per ticker would multiply a
    two-second check by the size of the basket."""
    calls = {"n": 0}

    def counted(bars, params):
        calls["n"] += 1
        return _honest(bars, params)

    computer = make_signal_computer("once", {"a": 1, "b": 2}, counted)
    bars = _bars()
    msg = {
        "type": "stock_history",
        "tickers": ["AAA", "BBB", "CCC"],
        "history": {"AAA": bars, "BBB": bars, "CCC": bars},
    }
    computer(msg)
    first = calls["n"]
    calls["n"] = 0
    computer(msg)
    second = calls["n"]

    # Second message: no verification at all, just the six real
    # computations (three tickers x two variants).
    assert second == 6
    assert first > second, (
        "the first message should cost more than the second -- it is "
        "the one that verifies"
    )


def test_a_context_taking_strategy_is_not_falsely_accused():
    """A strategy that reads cross-sectional context gets its context
    sliced to the truncated length. Without that, truncating history
    would leave signal[t] reading a context array still running to the
    end -- and every such strategy would be reported as peeking."""
    def with_context(bars, _params, context):
        market = (context or {}).get("market_returns") or []
        return [
            1.0 if t < len(market) and (market[t] or 0) > 0 else 0.0
            for t in range(len(bars))
        ]

    bars = _bars()
    computer = make_signal_computer("ctx", {"v1": None}, with_context)
    msg = _message(bars)
    msg["context"] = {
        "market_return_by_date": {b["date"]: 0.001 for b in bars},
        "per_ticker": {},
        "n_tickers": 1,
    }
    out = computer(msg)
    assert out[0][1] == "out"


# ── the copies stay identical ─────────────────────────────────────────


def test_the_skill_ships_the_same_checker_the_office_runs():
    """Two copies of a 559-line file. The office runs
    `roles/_contract_checks.py`; the skill bundles its own copy so that
    an assistant can invoke the fuller checks -- range, warm-up, a
    golden example -- which need declarations the office does not
    carry.

    Two copies is the shape that drifts, and the drift would be
    invisible: both files are individually fine, and the office would
    enforce one contract while the skill described another. So pin
    them.
    """
    office = (ROLES / "_contract_checks.py").read_bytes()
    bundled = (
        REPO_ROOT / "skills" / "backtest-strategy-builder"
        / "scripts" / "check_no_lookahead.py"
    ).read_bytes()
    assert office == bundled, (
        "skills/backtest-strategy-builder/scripts/check_no_lookahead.py "
        "has drifted from the office's roles/_contract_checks.py. Copy "
        "the office's version over it and rebuild the bundle -- the "
        "office's is the one that actually runs."
    )
