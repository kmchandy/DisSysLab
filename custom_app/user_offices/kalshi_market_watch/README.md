# Kalshi market watch

Streams **Kalshi discovery** updates: every poll scans **open events** and **open
markets** (when using a keyword), groups by **event**, then lists **all outcome
contracts** with implied % and return-at-ask hints.

## Modes

| `office.md` | Behavior |
|---------------|----------|
| `kalshi(keyword="oil", …)` | Matches `oil` on **open events** (titles, categories, …) *and* on **open markets** (rules, strikes), up to `max_scan_events` / `max_scan_markets`. Each hit pulls the **whole event** (all sibling outcomes). The events feed is what makes “iran” / “oil” work — the raw `/markets` stream is mostly sports. |
| `kalshi(series_ticker="KXWTI", …)` | Same pipeline, but only markets in that series (good for WTI oil without keyword noise). |
| `kalshi(ticker="KX…", …)` | Original single-ticker poll (no discovery). |

Discovery and explicit `ticker=` / `tickers=` cannot be combined.

## Run

From the **DisSysLab** repo root:

```bash
dsl run custom_app/user_offices/kalshi_market_watch/
```

Optional: `match_whole_word=true` on the keyword, `page_size`, `max_scan_events`,
`max_scan_markets`, `page_delay_seconds`, `event_expand_delay_seconds`,
`max_http_retries`, `backoff_cap_seconds`, `poll_interval`, `base_url` (demo vs prod).

## Note

Kalshi does **not** offer a public WebSocket in this source; “streaming” is
implemented as **frequent polling** with **one message per matching event** per
cycle so downstream agents see a steady stream of updates.

## Rate limits (429)

Discovery issues many HTTP requests (paged `/events`, `/markets`, then one
expansion per event). The source **paces** between pages, **sleeps** between
event expansions, and **retries** `429` / `503` with exponential backoff (and
`Retry-After` when present). Tune in `office.md`:

- **`page_delay_seconds`** — pause after each cursor page (default `0.2`).
- **`event_expand_delay_seconds`** — pause before each extra `event_ticker` fetch (default `0.15`).
- **`poll_interval`** — time between full discovery cycles; use **180–300** if you still hit limits.
- **`max_http_retries`** / **`backoff_cap_seconds`** — retry behavior for a single request.
