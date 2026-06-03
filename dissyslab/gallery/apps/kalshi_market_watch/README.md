# kalshi_market_watch

**Tags:** sense-and-respond, polling source, prediction markets, LLM analyst

Streams **Kalshi discovery** updates: every poll scans **open events** and
**open markets** (when using a keyword), groups by **event**, then lists
**all outcome contracts** with implied % and return-at-ask hints. One LLM
analyst summarises each event into a short briefing for the console and a
JSONL archive.

Originally built by Nyasha Makaya. The gallery version is a faithful copy
of his work; the original lives in his custom-app project.

## Run

```bash
dsl run kalshi_market_watch
```

You will see a briefing per event each poll cycle in the terminal, plus a
running `kalshi_market_watch.jsonl` archive in the current directory.

## Modes

The office is configured by editing the `Sources:` line in `office.md`.
Three modes are supported — pick one (you cannot combine discovery with an
explicit `ticker=`):

| `office.md` setting | Behaviour |
|---|---|
| `kalshi(keyword="oil", …)` | Matches `oil` on open events (titles, categories, …) and on open markets (rules, strikes), up to `max_scan_events` / `max_scan_markets`. Each hit pulls the whole event (all sibling outcomes). The events feed is what makes "iran" / "oil" work — the raw `/markets` stream is mostly sports. |
| `kalshi(series_ticker="KXWTI", …)` | Same pipeline, but only markets in the given series (good for WTI oil without keyword noise). |
| `kalshi(ticker="KX…", …)` | Original single-ticker poll (no discovery). |

The shipped office.md defaults to `keyword="gold"`. Change the keyword (or
switch to `series_ticker=...`) to track a different market.

## Rate limits

Discovery issues many HTTP requests (paged `/events`, `/markets`, then one
expansion per event). The source **paces** between pages, **sleeps** between
event expansions, and **retries** `429` / `503` with exponential backoff
(honouring `Retry-After` when present). Tunable knobs in `office.md`:

- `page_delay_seconds` — pause after each cursor page (default `0.25`).
- `event_expand_delay_seconds` — pause before each extra `event_ticker`
  fetch (default `0.2`).
- `poll_interval` — time between full discovery cycles. The default is
  180 (three minutes); raise to 240–300 if you still see `429`s.
- `max_http_retries` / `backoff_cap_seconds` — retry behaviour for a
  single request.

## Customise

- **Watch a different market**: edit the `keyword="..."` or
  `series_ticker="..."` argument in `office.md`.
- **Change the analyst's tone**: edit `roles/analyst.md` — it's a plain
  English prompt that produces the briefing. Currently emits a short,
  factual summary; rewrite for more colour, more bullishness, more
  scepticism, or whatever fits your trading style.
- **Add an email digest**: append a `gmail_sink(to="you@example.com", ...)`
  to the `Sinks:` line and to the `Alex's briefing is ...` connection
  line. When `GMAIL_USER` / `GMAIL_APP_PASSWORD` are set, the framework
  routes the digest to your address automatically (the `@example.com`
  placeholder is replaced at runtime).

## Output files (in the directory you ran `dsl run` from)

- `kalshi_market_watch.jsonl` — one line per event briefing. Useful for
  building a personal "what did the market look like last week" log.

## Note

Kalshi does **not** offer a public WebSocket through this source;
"streaming" is implemented as **frequent polling**, with one message per
matching event per cycle so downstream agents see a steady stream of
updates.
