# Manual, run-by-hand check -- NOT a pytest test, deliberately not under
# tests/ so CI never collects/executes it. Hits Stooq's real historical
# endpoint over the network; as of 2026-07-28 that endpoint 404s (see
# stock_history_source.py's module docstring and tests/unit/components/
# test_stock_history_source.py for the mocked, CI-safe version of this
# check). Run manually with: python3 scripts/manual_checks/check_stock_history_source.py

from dissyslab.components.sources.stock_history_source import StockHistorySource

src = StockHistorySource(tickers=["AAPL"])
msg = next(src.run())   # or: list(src.run())[0]
print (msg)
print(msg["history"]["AAPL"][:3])   # first few daily bars
print(msg.get("errors"))            # None if AAPL fetched cleanly
