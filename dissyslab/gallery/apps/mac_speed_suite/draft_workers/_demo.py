# dissyslab/gallery/apps/mac_speed_suite/draft_workers/_demo.py

"""
Manual smoke test for signal_computer.py + backtester.py + evaluator.py
-- runs the three worker FUNCTIONS directly, on synthetic price data.
This does NOT build or run a DisSysLab office (no office.md, no `dsl
build`/`dsl run` involved) -- it exists only so the worker bodies can
be checked by hand before anyone decides whether to wire them into a
real office.

JOIN itself (a plain `synchronizer_role`) isn't drafted here -- it's
an existing framework primitive, not app-specific code -- so this
script simulates what JOIN would hand to EVALUATOR by merging the
five BACKTESTER messages the same way `synchronizer_role` does (a
flat dict update across the five messages).

Usage:
    python3 _demo.py
"""

import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", ".."))

from dissyslab.components.sources.synthetic_stock_history_source import (
    SyntheticStockHistorySource,
)
from signal_computer import signal_computer, MAC_SPEEDS
from backtester import make_backtester
from evaluator import make_evaluator


def simulate_join(backtest_messages: list) -> dict:
    """What `synchronizer_role` would produce from these 5 messages."""
    merged: dict = {}
    for msg in backtest_messages:
        for k, v in msg.items():
            if k in merged and merged[k] != v:
                raise ValueError(f"JOIN merge conflict on key {k!r}")
            merged[k] = v
    return merged


def main():
    src = SyntheticStockHistorySource(
        tickers=["AAPL", "MSFT", "GOOGL"], start="2024-01-01", end="2025-09-30", seed=42,
    )
    history_msg = next(src.run())
    n_tickers = len(history_msg["tickers"])
    n_days = len(history_msg["history"]["AAPL"])
    print(f"1. Synthetic history: {history_msg['tickers']}, {n_days} trading days each\n")

    [(signals_msg, _port)] = signal_computer(history_msg)
    print(f"2. SIGNAL_COMPUTER: speeds={signals_msg['speeds']}  "
          f"ticker_volatility={ {k: round(v,3) for k,v in signals_msg['ticker_volatility'].items()} }\n")

    print("3. Five BACKTESTER workers:")
    backtest_messages = []
    for speed_name in MAC_SPEEDS:
        backtester_fn = make_backtester(speed_name)
        [(backtest_msg, _port)] = backtester_fn(signals_msg)
        backtest_messages.append(backtest_msg)
        n_ok = len(backtest_msg[speed_name]["per_ticker_returns"])
        print(f"   speed={speed_name:10s}  fast/slow={MAC_SPEEDS[speed_name]}  tickers_ok={n_ok}")

    joined_msg = simulate_join(backtest_messages)
    print(f"\n   JOIN merge OK -- keys: {sorted(joined_msg.keys())}\n")

    evaluator_fn = make_evaluator(rank_by="sharpe_ratio", target_annual_vol=0.10)
    [(eval_msg, _port)] = evaluator_fn(joined_msg)

    print(f"4. EVALUATOR table -- {len(eval_msg['table'])} stocks x "
          f"{len(MAC_SPEEDS)} speeds:")
    for ticker in eval_msg["table"]:
        row = eval_msg["table"][ticker]["fast"]
        print(f"   {ticker:6s} fast: ann_return={row['annualized_return']:+.3f}  "
              f"sharpe={row['sharpe_ratio']}")

    print(f"\n5. EVALUATOR portfolio_stats (rank_by={eval_msg['rank_by']!r}), ranked best->worst:")
    for name in eval_msg["ranked"]:
        s = eval_msg["portfolio_stats"][name]
        def fmt(x):
            return f"{x:+.3f}" if x is not None else "n/a"
        print(f"   {name:12s} ann_return={fmt(s['annualized_return'])}  "
              f"ann_vol={fmt(s['annualized_volatility'])}  "
              f"sharpe={fmt(s['sharpe_ratio'])}  calmar={fmt(s['calmar_ratio'])}")


if __name__ == "__main__":
    main()
