from dissyslab.components.sources.synthetic_stock_history_source import SyntheticStockHistorySource

src = SyntheticStockHistorySource(tickers=["AAPL", "MSFT"], start="2020-01-01", seed=42)
msg = next(src.run())
print(msg["history"]["AAPL"][:3])
