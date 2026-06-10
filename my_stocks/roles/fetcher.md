# Role: fetcher

## Purpose
Retrieve the most recent closing price for a given stock ticker from Yahoo Finance.

## Inputs
- ticker: string (e.g. "AAPL" or "TSLA")

## Outputs
- ticker: string
- closing_price: number (USD)
- price_date: date (the date the closing price corresponds to)

## Steps
1. Call the Yahoo Finance API (or yfinance library) for the given ticker
2. Extract the most recent closing price and its date
3. Return ticker, closing_price, and price_date

## Error handling
- If the fetch fails or returns no data, raise an error with the ticker name and a description of the failure
