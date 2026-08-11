#!/usr/bin/env python3
# dissyslab/gallery/apps/mac_speed_suite/download_stock_history_from_yf.py

"""
Fetch the daily price history this office backtests on.

The data is NOT shipped with the repository -- it is vendor data from Yahoo
Finance, and redistributing it would likely violate their terms. Each user
downloads their own copy in one command.

Two modes
---------

Fetch the office's whole basket (the common case). Reads the ticker list, the
data directory, and the filename pattern straight from ``office.md``, so there
is one source of truth and the download always matches what the office reads::

    python3 download_stock_history_from_yf.py

Fetch one ticker explicitly (for one-offs)::

    python3 download_stock_history_from_yf.py AAPL 10 AAPL_10_year.csv

Requires ``yfinance`` (``pip install yfinance``). Prices are split/dividend
adjusted (auto_adjust) and written as a clean
``Date,Open,High,Low,Close,Volume`` CSV that ``CSVStockHistorySource`` reads
directly.
"""

import os
import re
import sys

import yfinance as yf

HERE = os.path.dirname(os.path.abspath(__file__))
OFFICE_MD = os.path.join(HERE, "office.md")


def download_stock(ticker, years):
    """Return `years` of daily bars for one ticker as a clean DataFrame:
    a Date index and Open/High/Low/Close/Volume columns, split/dividend
    adjusted."""
    data = yf.download(
        ticker,
        period=f"{years}y",
        interval="1d",
        auto_adjust=True,
    )
    # yfinance returns MultiIndex columns like ("Close", "AAPL"); keep just the
    # metric name so the CSV has ONE clean header row (no "Ticker"/"Date" junk
    # rows).
    if hasattr(data.columns, "get_level_values"):
        data.columns = data.columns.get_level_values(0)
    data.index.name = "Date"
    return data[["Open", "High", "Low", "Close", "Volume"]]


def get_stock_data_save_to_csv(ticker, years, filename):
    download_stock(ticker, years).to_csv(filename)


def office_source_spec(office_md=OFFICE_MD):
    """Read (tickers, directory, filename_pattern, years) from office.md's
    ``csv_stock_history(...)`` source line -- the single source of truth.

    ``years`` is taken from the number in the filename pattern (e.g.
    ``{ticker}_10_year.csv`` -> 10), so the horizon is specified in one place
    too.
    """
    with open(office_md, encoding="utf-8") as f:
        text = f.read()
    call = re.search(r"csv_stock_history\((.*?)\)", text, re.DOTALL)
    if not call:
        raise SystemExit("Could not find csv_stock_history(...) in office.md")
    args = call.group(1)

    tick_m = re.search(r"tickers\s*=\s*\[([^\]]*)\]", args)
    tickers = (
        re.findall(r"['\"]([A-Za-z0-9.\-]+)['\"]", tick_m.group(1))
        if tick_m else []
    )
    dir_m = re.search(r"directory\s*=\s*['\"]([^'\"]+)['\"]", args)
    directory = dir_m.group(1) if dir_m else "."
    pat_m = re.search(r"filename_pattern\s*=\s*['\"]([^'\"]+)['\"]", args)
    pattern = pat_m.group(1) if pat_m else "{ticker}_1year.csv"
    yr_m = re.search(r"(\d+)_?year", pattern)
    years = int(yr_m.group(1)) if yr_m else 1
    return tickers, directory, pattern, years


def fetch_basket():
    """Download every ticker the office uses into the directory it reads
    from, named the way it expects."""
    tickers, directory, pattern, years = office_source_spec()
    if not tickers:
        raise SystemExit("No tickers found in office.md's csv_stock_history(...)")
    out_dir = os.path.normpath(os.path.join(HERE, directory))
    os.makedirs(out_dir, exist_ok=True)
    print(f"Fetching {years}y of daily data for {len(tickers)} ticker(s) "
          f"into {out_dir}")
    for ticker in tickers:
        ticker = ticker.upper()
        path = os.path.join(out_dir, pattern.format(ticker=ticker))
        get_stock_data_save_to_csv(ticker, years, path)
        print(f"  wrote {os.path.basename(path)}")
    print("Done. Now run:  dsl run .")


def main():
    if len(sys.argv) == 1:
        # Default: the office's whole basket, as described by office.md.
        fetch_basket()
    elif len(sys.argv) == 4:
        # Explicit single ticker: TICKER YEARS FILENAME.
        ticker, years, filename = sys.argv[1], int(sys.argv[2]), sys.argv[3]
        get_stock_data_save_to_csv(ticker, years, filename)
        print(f"wrote {filename}")
    else:
        print(
            "Usage:\n"
            "  python3 download_stock_history_from_yf.py"
            "            # fetch the office's basket (reads office.md)\n"
            "  python3 download_stock_history_from_yf.py TICKER YEARS FILENAME"
            "   # fetch one ticker"
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
