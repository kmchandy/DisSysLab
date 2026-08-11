import sys
import yfinance as yf


def download_stock(ticker, years):
    data = yf.download(
        ticker,
        period=f"{years}y",
        interval="1d",
        auto_adjust=True,
    )
    # yfinance returns MultiIndex columns like ("Close", "AAPL"); keep just the
    # metric name so the CSV has ONE clean header row (no "Ticker"/"Date" junk
    # rows) that the DisSysLab CSVStockHistorySource can read directly.
    if hasattr(data.columns, "get_level_values"):
        data.columns = data.columns.get_level_values(0)
    data.index.name = "Date"
    # Column order the DisSysLab CSV source expects (auto_adjust folds the
    # split/dividend adjustment into Close and drops "Adj Close").
    return data[["Open", "High", "Low", "Close", "Volume"]]


def get_stock_data_save_to_csv(ticker, years, filename):
    download_stock(ticker, years).to_csv(filename)


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print(
            "Usage: python3 download_stock_history_from_yf.py "
            "TICKER YEARS FILENAME"
        )
        sys.exit(1)

    ticker = sys.argv[1]
    years = int(sys.argv[2])
    filename = sys.argv[3]

    get_stock_data_save_to_csv(ticker, years, filename)

# Example usage (10 years, clean CSV named for the DisSysLab convention):
#   python3 download_stock_history_from_yf.py PLTR 10 ../../../sp100_data/PLTR_10_year.csv
# Output header: Date,Open,High,Low,Close,Volume  (data from row 2)
