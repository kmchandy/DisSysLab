"""Tests for ``StockHistorySource`` (registry name ``stock_history``).

These mock ``requests.get`` rather than hitting Stooq for real: this
environment's outbound network access to financial-data sites
(Stooq included) is blocked, so a live-network test would simply
fail here regardless of whether the class is correct. Run a manual
smoke test against the real endpoint from a machine with normal
internet access before relying on this in production.
"""

from __future__ import annotations

from unittest.mock import Mock, patch

from dissyslab.components.sources.stock_history_source import StockHistorySource

_AAPL_CSV = (
    "Date,Open,High,Low,Close,Volume\n"
    "2024-01-02,185.10,188.30,184.90,187.42,58414500\n"
    "2024-01-03,186.00,189.00,185.50,188.10,50000000\n"
)

_MSFT_CSV = (
    "Date,Open,High,Low,Close,Volume\n"
    "2024-01-02,370.00,375.00,368.00,373.50,20000000\n"
)

_NO_DATA = "No data\n"


def _resp(text: str) -> Mock:
    m = Mock()
    m.text = text
    m.raise_for_status = Mock()
    return m


def test_bulk_message_shape_for_multiple_tickers() -> None:
    src = StockHistorySource(tickers=["AAPL", "MSFT"], request_pause=0)

    with patch("requests.get", side_effect=[_resp(_AAPL_CSV), _resp(_MSFT_CSV)]):
        messages = list(src.run())

    # One-shot generator: exactly one bulk message, then stop.
    assert len(messages) == 1
    msg = messages[0]

    assert msg["type"] == "stock_history"
    assert msg["tickers"] == ["AAPL", "MSFT"]
    assert "errors" not in msg

    assert msg["history"]["AAPL"] == [
        {"date": "2024-01-02", "open": 185.10, "high": 188.30,
         "low": 184.90, "close": 187.42, "volume": 58414500.0},
        {"date": "2024-01-03", "open": 186.00, "high": 189.00,
         "low": 185.50, "close": 188.10, "volume": 50000000.0},
    ]
    assert msg["history"]["MSFT"][0]["close"] == 373.50


def test_ticker_normalization_and_request_params() -> None:
    src = StockHistorySource(
        tickers=["aapl"], start="2015-01-01", end="2025-01-01", request_pause=0
    )
    assert src.tickers == ["aapl.us"]
    assert src.start == "20150101"
    assert src.end == "20250101"

    with patch("requests.get", return_value=_resp(_AAPL_CSV)) as mock_get:
        list(src.run())

    _, kwargs = mock_get.call_args
    assert kwargs["params"]["s"] == "aapl.us"
    assert kwargs["params"]["d1"] == "20150101"
    assert kwargs["params"]["d2"] == "20250101"


def test_non_us_ticker_is_not_suffixed() -> None:
    src = StockHistorySource(tickers=["ntt.jp"], request_pause=0)
    assert src.tickers == ["ntt.jp"]
    assert src.display_tickers == ["NTT"]


def test_one_bad_ticker_does_not_sink_the_others() -> None:
    src = StockHistorySource(tickers=["AAPL", "BAD"], request_pause=0)

    with patch("requests.get", side_effect=[_resp(_AAPL_CSV), _resp(_NO_DATA)]):
        messages = list(src.run())

    msg = messages[0]
    assert "AAPL" in msg["history"]
    assert "BAD" not in msg["history"]
    assert "BAD" in msg["errors"]
    assert "no data" in msg["errors"]["BAD"].lower()


def test_requires_at_least_one_ticker() -> None:
    try:
        StockHistorySource(tickers=[])
        assert False, "expected ValueError for empty tickers"
    except ValueError:
        pass


def test_rejects_malformed_date() -> None:
    try:
        StockHistorySource(tickers=["AAPL"], start="01/01/2020")
        assert False, "expected ValueError for malformed date"
    except ValueError:
        pass
