# Stocks Monitor

> A plain-English read of a stock ticker every few minutes, on
> your laptop. Free.

`stocks_monitor` polls a live price feed for one ticker and writes
a one-line briefing: *up 1.2%, holding steady, down on heavy
volume.* No subscription, no trading-platform sign-up, no API key.

A simple one-source / one-agent / one-sink office — good as a
second office to read after `weather_monitor` if you're learning
the framework.

## Set it up in 5 minutes

If you've already run another DSL office, just:

```bash
dsl run dissyslab/gallery/apps/stocks_monitor/
```

If this is your first DSL office, see the
[top-level README](../../../../README.md) for the one-line
installer.

Default ticker is `AAPL`, polled every 5 minutes. Change either in
`office.md`.

## What you'll see

Each poll, a one-line briefing appears in your terminal:

```
[Alex]  AAPL is trading at $187.42 — up 1.3% on the session, in
        line with the broader tech rally. No action warranted.
```

The same line is appended to `stocks_monitor.jsonl` for downstream
tools.

## Make it yours

### Tier 1 — Tweak  *(5 minutes, one parameter)*

Change the ticker or the polling cadence in `office.md`:

```
Sources: stocks(ticker="MSFT", poll_interval=600)
```

`poll_interval` is seconds. `300` = every 5 minutes; `60` = every
minute; `3600` = once an hour.

### Tier 2 — Modify  *(30 minutes, swap a component)*

**Track several tickers at once.** List multiple sources:

```
Sources: stocks(ticker="AAPL"), stocks(ticker="MSFT"), stocks(ticker="GOOG")
Connections:
stocks's destination is Alex.   # each source streams to the same Alex
```

Alex sees each tick as it arrives.

**Filter for big moves only.** Edit
[`roles/analyst.md`](roles/analyst.md) so Alex routes to two ports
— `big_move` and `quiet`:

```
If the price moved more than 2% since the last quote, send to
big_move. Otherwise send to quiet.
```

Then route `Alex's big_move` to a notification sink and
`Alex's quiet` to discard.

**Use Claude for high-stakes alerts only.** Most of the time Qwen
is fine. Override one role to use Claude (see
[`situation_room_pro`](../situation_room_pro/) for the pattern).

### Tier 3 — Build  *(a few hours)*

Combine `stocks` with a news source. When Alex spots a 3% move on
AAPL, simultaneously query recent BBC tech / TechCrunch headlines
about Apple and write a one-paragraph "what's behind this move"
brief. That's a real multi-source office. See
[`docs/BUILD_APPS.md`](../../../../docs/BUILD_APPS.md).

## What you should expect

- **Quality**: factual price reads plus light commentary. Qwen3
  doesn't speculate beyond what's in the data.
- **Speed**: ~10-30 seconds per briefing. Frequency depends on
  `poll_interval`.
- **Cost**: $0/month recurring. The price source uses a free Yahoo
  Finance feed.
- **Privacy**: only the ticker symbol leaves your machine.

## ⚠ Not investment advice

This is a personal-notification office. Alex's briefings are
literal reads of the price data — not financial advice, not trade
signals, not predictions. The framework is decent at "summarise
this thing" and unreliable at "predict the future." If you're
building a trading system, you want lower latency and a different
architecture.

## See also

- [`office.md`](office.md) — the wiring.
- [`roles/analyst.md`](roles/analyst.md) — Alex's job description.
- [`weather_monitor`](../weather_monitor/README.md) — the same
  shape with a different source. Useful comparison if you're
  learning.
