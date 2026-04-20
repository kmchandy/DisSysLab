# Stocks Monitor

Monitors a stock ticker's price and delivers one-sentence updates on
whether it's rising, falling, or holding steady — with commentary about
whether any action is warranted.

## What it does

- Polls a live price feed every five minutes for the ticker you choose
- A financial analyst agent writes a short briefing that interprets the
  movement in plain English
- Output streams to your terminal and to `stocks_monitor.jsonl`

## Try it

```bash
dsl init stocks_monitor my_stocks
cd my_stocks
dsl run .
```

## Make it yours

- Change the ticker in `office.md`: `Sources: stocks(ticker="AAPL", poll_interval=300)`
- Rewrite the analyst in `roles/analyst.md` to focus on specific signals
  (moving averages, volatility, volume spikes)
- Add a second agent that tracks multiple tickers and compares them
