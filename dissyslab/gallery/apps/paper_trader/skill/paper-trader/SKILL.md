---
name: paper-trader
description: Configure and operate the DisSysLab paper_trader app -- a daily paper-trading office that advances a simulated book forward using a committed strategy. Use this whenever the user wants to set up, run, tune, inspect, or compare a paper-trading book: "start a paper-trading book", "run my paper trader", "trade the SP100 with a moving-average strategy on paper", "what do I hold", "why did we exit NVDA", "compare my paper books", "use a tighter stop", "run this every trading day". STRICTLY paper -- simulated fills only, never real orders. Requires the DisSysLab repo, specifically dissyslab/gallery/apps/paper_trader/.
---

# Operating the paper_trader app

The paper_trader office (`dissyslab/gallery/apps/paper_trader/`) advances a
simulated book one trading day at a time: decide on the prior close, fill at the
next open, append the day to an event-sourced ledger, and print/write a brief.
All correctness lives in tested modules; you (Cowork) configure and drive it.
**Strictly paper: simulated fills only, never place a real order.**

## Files per book (in a book directory, default `book/`)

- `config.json` -- the user-edited genesis config (you edit this). Optional;
  absent -> sensible defaults.
- `ledger.jsonl` -- append-only event log, the **source of truth** (written by
  the app; you only ever *append* a correction, never edit past lines).
- `book.json` -- derived snapshot cache (written by the app).
- `brief.html` / `brief.txt` -- the latest day's action list.

## Configure a book (write `book/config.json`)

From an English description, write `config.json` as a genesis:

```json
{ "type": "genesis", "strategy": "mac_fast",
  "starting_cash": 100000.0,
  "universe": ["AMD","NFLX","NVDA","PLTR","TSLA"],
  "initial_positions": { "AMD": {"shares": 100, "cost_basis": 138.20} },
  "policy": { "sizing": "inverse_vol", "stop_pct": 0.10, "cost_bps": 5.0,
              "slippage_bps": 0.0, "no_trade_band": 0.005,
              "exit_policy": "market_defined" } }
```

Defaults if the user doesn't specify: SP-style basket from the office, $100k,
flat (no positions), `inverse_vol` sizing, 10% stop, 5 bps cost. **Always echo
the assumptions back before the first run.** `initial_positions` is how a user
seeds real current holdings (the app's core "given what I hold" question);
`cost_basis` defaults to the first-run open if omitted (say so).

## Run / catch up / replay

- `dsl run .` in the office folder runs the book forward over every
  not-yet-committed trading day (catch-up is automatic; re-runs are safe).
- To replay only up to a past date (fast historical testing), set the `as_of`
  arg on the `TRADER` line in `office.md`, or ask and set it.
- To schedule it daily, set up a scheduled task that runs `dsl run .` after the
  close on trading days (the "supervisor"); the book is idempotent so a missed
  day just catches up.

## Change policy (edit `config.json`'s `policy`)

Any field in English: `sizing` (`inverse_vol` default, `equal_weight`,
`fixed_fraction`, `risk_based`), `stop_pct`, `cost_bps`, `no_trade_band`,
`exit_policy`. Re-stamp and re-run. If the user asks for `exit_policy:
"realized_entry"`, tell them it requires the fill-modeling backtester and is not
yet built (it raises on purpose) -- offer `market_defined` instead.

## Generate a new strategy (Tier 3) — offer the self-check, never skip it

The user can ask you to *invent* a new strategy ("try a momentum strategy",
"buy when it's 5% above its 50-day average"). This is the most powerful thing she
can do and the most dangerous: a strategy that peeks at future prices looks
brilliant in backtest and loses money live. So:

1. Write the strategy as a `compute_fn(bars, params) -> [signal_per_bar]` where
   `signal[t]` uses only `bars[0..t]` (no look-ahead). Add it to `strategies.py`.
2. **Before trading on it, offer to run the self-check** and show the result:

   ```python
   from strategy_selfcheck import run_selfcheck, format_report
   print(format_report(run_selfcheck(my_fn, bars, params)))
   ```

   It runs three mechanical checks — contract (one finite signal per bar),
   determinism, and **look-ahead** (recomputes on truncated history and fails if
   any earlier decision moves when future bars are added). Offer a bespoke
   `known_case` assertion too when the user describes expected behaviour.
3. **Advise, don't force.** If she wants to explore without testing, let her —
   but say plainly that an untested generated strategy is not safe to trade on,
   and that the look-ahead check is the one that catches the classic trap. If the
   check FAILS, do not paper-trade on it; offer to fix the peeking and re-run.

This is the whole point of the tested substrate: Cowork alone cannot prove a
strategy isn't cheating — it needs this harness to run the check in.

## Multiple strategies = independent books

To compare strategies live, give each its own book directory and its own
`TRADER` line / office copy -- completely independent, no shared state. Then read
their ledgers and build whatever comparison the user wants (there is no shipped
aggregator; you write it on request).

## Answer questions / correct mistakes

- "What do I hold / what changed / why did we do X?" -> read `book.json`,
  `brief.txt`, and the `decisions` trace in the latest `ledger.jsonl` run line.
- Correct a wrong fill by **appending** a `{"type":"compensation","reverses":
  "<order_id>","fills":[...]}` line to `ledger.jsonl` -- never edit a past line.
  The app re-checks the snapshot==replay invariant on the next run.

## Guardrails (always)

Disclose the assumptions you filled in; correct via compensation events, never
edits; never bypass the ledger/invariant; run the strategy self-check on anything
you generate (and heed a FAIL); and it is **paper only** -- never wire in a real
broker or place a real order.
