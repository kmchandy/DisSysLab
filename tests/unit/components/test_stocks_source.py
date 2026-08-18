"""Tests for the yfinance-backed ``stocks`` source.

No network. yfinance is stubbed, because the point of these tests is the
contract between the source and everything downstream — the message
shape, the ticker normalisation, and what happens when the optional
dependency is absent. Whether Yahoo is up today is not something a test
suite should have an opinion about.

Context: this source read Stooq until 2026-08-18. Stooq's quote endpoint
was removed and its history endpoint now serves a JavaScript challenge.
The switch to yfinance carries a constraint — Yahoo's terms forbid
redistributing their data, so every user fetches their own and the
repository ships no prices at all.
"""
from __future__ import annotations

import sys
import types

import pytest

from dissyslab.components.sources.stocks_source import StocksSource


# ── A stand-in for yfinance ──────────────────────────────────────────────
#
# `fast_info` raises rather than returning None for missing fields on some
# symbols, which is the awkward part of the real API and the reason
# `_number` catches broadly. The stub reproduces that on purpose: a stub
# that politely returns None would let a regression through.


class _FastInfo:
    def __init__(self, **values):
        self._values = values

    def __getattr__(self, name):
        try:
            return self._values[name]
        except KeyError:
            raise KeyError(name) from None


class _Ticker:
    def __init__(self, symbol, **kwargs):
        _Ticker.last_symbol = symbol
        _Ticker.last_kwargs = kwargs
        self.fast_info = _Ticker.fast_info_to_return


def _install_stub(monkeypatch, **fields):
    module = types.ModuleType("yfinance")
    _Ticker.fast_info_to_return = _FastInfo(**fields)
    module.Ticker = _Ticker
    monkeypatch.setitem(sys.modules, "yfinance", module)
    return module


HEALTHY = dict(
    last_price=305.59,
    previous_close=300.0,
    open=306.21,
    day_high=307.66,
    day_low=302.94,
    currency="USD",
    exchange="NMS",
)


def _one(source):
    """Pull a single message out of the generator."""
    return next(iter(source.run()))


# ── Message shape ────────────────────────────────────────────────────────


def test_message_keeps_the_documented_shape(monkeypatch):
    """Downstream sinks route on these keys. The provider changed; the
    contract deliberately did not."""
    _install_stub(monkeypatch, **HEALTHY)
    msg = _one(StocksSource(ticker="AAPL", max_readings=1))
    assert set(msg) == {
        "type", "ticker", "market", "price", "open", "high", "low",
        "previous_close", "change", "change_pct", "currency",
        "market_date", "market_time", "timestamp",
    }
    assert msg["type"] == "stocks"
    assert msg["price"] == 305.59
    assert msg["currency"] == "USD"


def test_change_is_measured_against_previous_close(monkeypatch):
    """Changed from the Stooq version, which measured against the session
    open. "Up 2% today" means since yesterday's close everywhere else a
    student will meet it."""
    _install_stub(monkeypatch, **HEALTHY)
    msg = _one(StocksSource(ticker="AAPL", max_readings=1))
    assert msg["change"] == pytest.approx(5.59)
    assert msg["change_pct"] == pytest.approx(1.863, abs=0.001)


def test_missing_fields_become_none_rather_than_crashing(monkeypatch):
    """`fast_info` raises for absent fields on thinly traded symbols. A
    price we have plus a high we do not should still produce a usable
    message."""
    _install_stub(monkeypatch, last_price=10.0, currency="USD")
    msg = _one(StocksSource(ticker="XYZ", max_readings=1))
    assert msg["price"] == 10.0
    assert msg["high"] is None and msg["low"] is None
    assert msg["change"] is None and msg["change_pct"] is None


def test_zero_previous_close_does_not_divide_by_zero(monkeypatch):
    _install_stub(monkeypatch, last_price=10.0, previous_close=0)
    msg = _one(StocksSource(ticker="XYZ", max_readings=1))
    assert msg["change"] is None and msg["change_pct"] is None


# ── Ticker normalisation ─────────────────────────────────────────────────


@pytest.mark.parametrize(
    "written,sent",
    [
        ("AAPL", "AAPL"),
        ("aapl", "AAPL"),
        ("  aapl  ", "AAPL"),
        ("aapl.us", "AAPL"),      # the Stooq spelling, in our own old examples
        ("AAPL.US", "AAPL"),
        ("BP.L", "BP.L"),         # Yahoo market codes survive untouched
        ("7203.T", "7203.T"),
    ],
)
def test_ticker_normalisation(monkeypatch, written, sent):
    _install_stub(monkeypatch, **HEALTHY)
    _one(StocksSource(ticker=written, max_readings=1))
    assert _Ticker.last_symbol == sent


# ── Failure is reported as data, and named ───────────────────────────────


def test_no_price_yields_an_error_message_not_a_crash(monkeypatch):
    """A symbol that does not exist looks exactly like a symbol with no
    data, so the message says so."""
    _install_stub(monkeypatch, currency="USD")   # no last_price
    msg = _one(StocksSource(ticker="NOTATICKER", max_readings=1))
    assert msg["type"] == "stocks_error"
    assert "NOTATICKER" in msg["error"]


def test_missing_yfinance_names_the_install_command(monkeypatch):
    """The whole reason the import is deferred. A student who wires up
    `stocks` without the extra must get the command, not a traceback —
    and `Network._raise_if_no_source_produced_output` quotes this text
    verbatim in the run summary."""
    monkeypatch.setitem(sys.modules, "yfinance", None)   # forces ImportError
    msg = _one(StocksSource(ticker="AAPL", max_readings=1))
    assert msg["type"] == "stocks_error"
    assert "dissyslab[market]" in msg["error"]


def test_the_module_imports_without_yfinance():
    """`SOURCE_REGISTRY` imports this module to resolve the name
    `stocks`, so a top-level `import yfinance` would break `dsl check`
    for every office in the gallery on a machine without the extra.

    The import at the top of this file already proves it for this
    process; this asserts the property explicitly so the reason is
    recorded next to the check.
    """
    import dissyslab.components.sources.stocks_source as mod

    assert not hasattr(mod, "yfinance"), (
        "yfinance must not be imported at module scope — see _yf()"
    )
