"""Tests for ``SyntheticStockHistorySource`` (registry name
``synthetic_stock_history``). No network involved -- these run
directly, no mocking needed.
"""

from __future__ import annotations

from dissyslab.components.sources.synthetic_stock_history_source import (
    SyntheticStockHistorySource,
)


def test_bulk_message_shape_matches_stock_history() -> None:
    src = SyntheticStockHistorySource(
        tickers=["AAPL", "MSFT"], start="2024-01-01", end="2024-01-10", seed=1
    )
    messages = list(src.run())

    assert len(messages) == 1  # one-shot generator
    msg = messages[0]

    assert msg["type"] == "stock_history"
    assert msg["synthetic"] is True
    assert msg["tickers"] == ["AAPL", "MSFT"]
    assert msg["start"] == "20240101"
    assert msg["end"] == "20240110"
    assert set(msg["history"]) == {"AAPL", "MSFT"}

    bar = msg["history"]["AAPL"][0]
    assert set(bar) == {"date", "open", "high", "low", "close", "volume"}
    assert bar["high"] >= bar["open"]
    assert bar["high"] >= bar["close"]
    assert bar["low"] <= bar["open"]
    assert bar["low"] <= bar["close"]


def test_trading_days_exclude_weekends() -> None:
    # 2024-01-06 and 2024-01-07 are a Sat/Sun.
    src = SyntheticStockHistorySource(
        tickers=["AAPL"], start="2024-01-05", end="2024-01-08", seed=1
    )
    msg = next(src.run())
    dates = [bar["date"] for bar in msg["history"]["AAPL"]]
    assert dates == ["2024-01-05", "2024-01-08"]


def test_same_seed_is_reproducible() -> None:
    kwargs = dict(tickers=["AAPL", "MSFT"], start="2024-01-01", end="2024-03-01", seed=7)
    msg1 = next(SyntheticStockHistorySource(**kwargs).run())
    msg2 = next(SyntheticStockHistorySource(**kwargs).run())
    assert msg1["history"] == msg2["history"]


def test_seed_reproducible_across_processes() -> None:
    """Regression test for the Python 3.11+ ``random.Random((seed, ticker))``
    TypeError bug: the fix must not rely on ``hash()``, whose value for
    strings is randomized per-process (``PYTHONHASHSEED``) unless
    disabled. Spawn a fresh subprocess (a fresh hash seed) and confirm
    it reproduces the same in-process result -- this would have caught
    a ``hash()``-based "fix" that merely swapped one non-reproducible
    mechanism for another.
    """
    import subprocess
    import sys
    import json
    import os

    here = os.path.dirname(os.path.abspath(__file__))
    module_path = os.path.join(
        here, "..", "..", "..",
        "dissyslab", "components", "sources", "synthetic_stock_history_source.py",
    )
    script = f"""
import importlib.util
spec = importlib.util.spec_from_file_location("m", {module_path!r})
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
src = m.SyntheticStockHistorySource(
    tickers=["AAPL", "MSFT"], start="2024-01-01", end="2024-01-05", seed=7
)
msg = next(src.run())
import json
print(json.dumps(msg["history"]))
"""
    in_process = next(
        SyntheticStockHistorySource(
            tickers=["AAPL", "MSFT"], start="2024-01-01", end="2024-01-05", seed=7
        ).run()
    )["history"]

    out = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True, text=True, timeout=30,
    )
    assert out.returncode == 0, out.stderr
    subprocess_result = json.loads(out.stdout)
    assert subprocess_result == in_process


def test_different_tickers_do_not_share_a_path() -> None:
    src = SyntheticStockHistorySource(
        tickers=["AAPL", "MSFT"], start="2024-01-01", end="2024-03-01", seed=7
    )
    msg = next(src.run())
    assert msg["history"]["AAPL"] != msg["history"]["MSFT"]


def test_no_seed_gives_different_runs() -> None:
    kwargs = dict(tickers=["AAPL"], start="2024-01-01", end="2024-03-01")
    msg1 = next(SyntheticStockHistorySource(**kwargs).run())
    msg2 = next(SyntheticStockHistorySource(**kwargs).run())
    assert msg1["history"] != msg2["history"]


def test_initial_price_dict_per_ticker() -> None:
    src = SyntheticStockHistorySource(
        tickers=["AAPL", "MSFT"],
        start="2024-01-01",
        end="2024-01-02",
        initial_price={"AAPL": 150.0, "MSFT": 300.0},
        seed=1,
    )
    msg = next(src.run())
    assert msg["history"]["AAPL"][0]["open"] == 150.0
    assert msg["history"]["MSFT"][0]["open"] == 300.0


def test_unlisted_ticker_falls_back_to_default_price() -> None:
    src = SyntheticStockHistorySource(
        tickers=["AAPL", "GOOGL"],
        start="2024-01-01",
        end="2024-01-02",
        initial_price={"AAPL": 150.0},
        seed=1,
    )
    msg = next(src.run())
    assert msg["history"]["GOOGL"][0]["open"] == 100.0


def test_requires_at_least_one_ticker() -> None:
    try:
        SyntheticStockHistorySource(tickers=[])
        assert False, "expected ValueError for empty tickers"
    except ValueError:
        pass


def test_end_before_start_raises() -> None:
    try:
        SyntheticStockHistorySource(tickers=["AAPL"], start="2024-06-01", end="2024-01-01")
        assert False, "expected ValueError for end before start"
    except ValueError:
        pass
