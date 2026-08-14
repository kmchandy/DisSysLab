"""
Tests for the EXITS slot. Pure Python:

    python3 -m pytest test_exits.py -q
"""

from __future__ import annotations

import pytest

from exits import apply_exits


def test_market_defined_is_a_pass_through():
    signals = {"A": 1, "B": 0, "C": -1}
    out = apply_exits(signals, {"A": 100}, {"A": 143.0}, book=None,
                      policy={"exit_policy": "market_defined"})
    assert out == signals and out is not signals   # a copy, unchanged


def test_default_policy_is_market_defined():
    signals = {"A": 1}
    assert apply_exits(signals, {}, {}, None, {}) == signals


def test_realized_entry_refuses_loudly_until_built():
    with pytest.raises(NotImplementedError):
        apply_exits({"A": 1}, {}, {}, None, {"exit_policy": "realized_entry"})


def test_unknown_exit_policy_raises():
    with pytest.raises(ValueError):
        apply_exits({"A": 1}, {}, {}, None, {"exit_policy": "bogus"})
