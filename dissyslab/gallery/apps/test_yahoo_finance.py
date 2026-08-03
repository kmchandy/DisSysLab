from pathlib import Path

import yfinance as yf


# Five volatile-leaning S&P 100 stocks
TICKERS = ["TSLA", "NVDA", "AMD", "PLTR", "NFLX"]

# Create a folder for the downloaded files
OUTPUT_DIRECTORY = Path("sp100_data")
OUTPUT_DIRECTORY.mkdir(exist_ok=True)

# Download one year of daily data
data = yf.download(
    tickers=TICKERS,
    period="1y",
    interval="1d",
    auto_adjust=False,
    group_by="ticker",
    progress=False,
    threads=True,
)

if data.empty:
    raise RuntimeError("No stock data was downloaded.")

# Save all five stocks in one file
combined_path = OUTPUT_DIRECTORY / "five_sp100_stocks.csv"
data.to_csv(combined_path)

# Also save a separate CSV file for each stock
for ticker in TICKERS:
    ticker_data = data[ticker].dropna(how="all")

    if ticker_data.empty:
        print(f"Warning: no data found for {ticker}")
        continue

    output_path = OUTPUT_DIRECTORY / f"{ticker}_1year.csv"
    ticker_data.to_csv(output_path)

    print(f"{ticker}: saved {len(ticker_data)} rows to {output_path}")

print(f"\nCombined data saved to {combined_path}")