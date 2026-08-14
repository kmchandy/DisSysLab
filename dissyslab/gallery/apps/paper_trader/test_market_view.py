"""
Tests for the market_view adapter (pure). Uses a toy compute_fn so it is
independent of any real strategy:

    python3 -m pytest test_market_view.py -q
"""

from __future__ import annotations

import pytest

from market_view import all_trading_dates, as_of_view


def _bars(dates, closes, opens=None):
    opens = opens or closes
    return [{"date": d, "open": o, "high": c, "low": c, "close": c, "volume": 0}
            for d, o, c in zip(dates, opens, closes)]


def sma_cross(bars, params):
    """Toy strategy: long (1) if the last close is above the mean close, else 0."""
    closes = [b["close"] for b in bars]
    m = sum(closes) / len(closes)
    return [1.0 if c > m else 0.0 for c in closes]


DATES = [f"2020-01-{i:02d}" for i in range(1, 11)]           # 10 trading days


def test_all_trading_dates_is_sorted_union():
    hist = {"A": _bars(DATES[:5], [1, 2, 3, 4, 5]),
            "B": _bars(DATES[2:7], [1, 1, 1, 1, 1])}
    assert all_trading_dates(hist) == DATES[:7]


def test_as_of_decides_on_prior_close_and_fills_at_open():
    # rising series: last close always above the running mean -> signal 1
    hist = {"A": _bars(DATES, list(range(1, 11)), opens=[x + 0.5 for x in range(1, 11)])}
    v = as_of_view(hist, "2020-01-05", sma_cross, {})
    assert v["trade_date"] == "2020-01-05"
    assert v["signals"]["A"] == 1.0                          # decided on bars up to 01-04
    assert v["close_tminus1"]["A"] == 4                       # prior close
    assert v["open_t"]["A"] == pytest.approx(5.5)            # open on 01-05 (the fill)
    assert v["vols"]["A"] is not None


def test_no_lookahead_signal_ignores_the_as_of_bar():
    # engineer a spike ON the as-of date that would flip the signal if used
    closes = [10, 10, 10, 10, 100]           # 01-05 close is a spike
    hist = {"A": _bars(DATES[:5], closes)}
    v = as_of_view(hist, "2020-01-05", sma_cross, {})
    # decision uses only 01-01..01-04 (all equal) -> last close not above mean -> 0
    assert v["signals"]["A"] == 0.0
    assert v["close_tminus1"]["A"] == 10                     # not the 100 spike


def test_first_date_has_no_prior_close():
    hist = {"A": _bars(DATES[:3], [1, 2, 3])}
    with pytest.raises(ValueError):
        as_of_view(hist, DATES[0], sma_cross, {})


def test_unknown_as_of_date_raises():
    hist = {"A": _bars(DATES[:3], [1, 2, 3])}
    with pytest.raises(ValueError):
        as_of_view(hist, "1999-01-01", sma_cross, {})
