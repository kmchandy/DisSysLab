from dissyslab.components.sources.stock_history_source import StockHistorySource

src = StockHistorySource(tickers=["AAPL"])
msg = next(src.run())   # or: list(src.run())[0]
print (msg)
print(msg["history"]["AAPL"][:3])   # first few daily bars
print(msg.get("errors"))            # None if AAPL fetched cleanly
