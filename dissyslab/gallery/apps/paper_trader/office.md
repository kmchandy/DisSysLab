# Office: paper_trader

# A daily paper-trading office. On each `dsl run .` it reads the price history,
# advances the book forward over every not-yet-processed trading day (catch-up /
# replay), and prints a brief. All correctness lives in the tested pure modules
# (paper_ledger, paper_store, market_view, risk_sizer, exits, order_generator,
# paper_broker) composed by the TRADER agent's day_runner.
#
# Get the data the same way as the backtester (from the repo root):
#   cd dissyslab/gallery/apps/mac_speed_suite && python3 download_stock_history_from_yf.py
# then run this office:
#   cd ../paper_trader && dsl run .
#
# The book lives in ./book/ (config.json is the optional user-edited genesis;
# ledger.jsonl + book.json are written by the store). Configure by talking to
# Cowork, or edit ./book/config.json. Strictly paper -- simulated fills only.

Sources: csv_stock_history(tickers=['AMD', 'NFLX', 'NVDA', 'PLTR', 'TSLA'], directory='../../../../sp100_data', filename_pattern='{ticker}_10_year.csv')
Sinks: console_printer

Agents:
# strategy is a per-ticker rule (MVP: mac_fast). as_of caps the replay at a date;
# unset = today (latest date in the data). Policy (sizing, stop, cost, no-trade
# band, exit policy) lives in book/config.json, defaulting sensibly.
TRADER is a trader(book_dir='book', strategy='mac_fast').

Connections:
csv_stock_history's out is TRADER.
TRADER's out is console_printer.
