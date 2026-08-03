# Manual, run-by-hand check -- NOT a pytest test, deliberately not under
# tests/ so CI never collects/executes it (it has no assertions, only
# prints). See tests/unit/components/test_synthetic_stock_history_source.py
# for the real, assertion-based CI test of this source. Run manually with:
# python3 scripts/manual_checks/check_synthetic_stock_history_source.py

from dissyslab.components.sources.synthetic_stock_history_source import SyntheticStockHistorySource

src = SyntheticStockHistorySource(tickers=["AAPL", "MSFT"], start="2020-01-01", seed=42)
msg = next(src.run())
print(msg["history"]["AAPL"][:3])
