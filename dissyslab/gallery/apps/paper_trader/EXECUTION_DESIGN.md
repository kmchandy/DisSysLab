# paper_trader — execution app design

*The second half of the trading app: a live paper-trading office that decides and
records simulated trades day by day. Design doc for review; no code written yet.
Working app name `paper_trader` (rename freely). Companion to the backtester
(`mac_speed_suite`) — reuses its strategy roles, answers a different question.*

## What this app is (and is not)

The backtester answers *"is this strategy any good?"* — it wants history,
statistics, and out-of-sample discipline. This app answers the separate question
*"given what I hold, what should I do tomorrow?"* — it wants today's state,
current positions, what changed since yesterday, and what's near a level, with
almost no statistics. Serving both from one output makes both worse, so this is a
distinct office.

**Paper trades only.** Fills are simulated and written to a local ledger. There
is no brokerage, no credentials, and no code path that could place a real order.
This is a hard line, not a later toggle: automating real-money execution is out
of scope permanently. Paper execution loses nothing pedagogically or as a
demonstration.

It reuses the backtester's signal-computer roles unchanged. The only difference
is what happens to the signal: the backtester multiplies it against historical
returns; here the *latest* signal becomes today's target position, and everything
downstream (sizing, reconciliation, execution, the book) is new.

## The mental model: each day is a transaction

One run per day, triggered by the scheduler after the close on trading days. A run
reads the book as of yesterday, decides today's target positions, fills the needed
orders as paper trades, writes a new book, emits a brief, and terminates. Nothing
runs continuously — "always-on" is the scheduler, not a long-lived process, which
is why this is a single thread-based office and does not need offices-as-processes
to be correct. If a run crashes midway, yesterday's book is untouched and
re-running the day is safe (see idempotency, below).

Because each daily run is a terminating pipeline that carries durable state
forward, it is architecturally close to the backtester (batch + terminate) plus a
durable book, an idempotent execution step, and a scheduler.

## Office structure

A single office; a DAG that terminates each run.

```
Sources:
  market_today   — recent bars up to today for the basket (lookback enough to warm the signal)
  current_book   — reads the durable book (positions, cash, open lots, ledger) at run start

Agents:
  MKT     market_context     (only if the live strategy uses relative strength)      [reused]
  SIGNAL  <committed strategy's signal computer>  -> today's target signal per ticker  [reused]
  EXITS   exit_policy        target signals + current book (+ prices) -> adjusted targets
                             (OPTIONAL, pluggable: default market-defined stops [book-
                              independent]; opt-in realized-entry stops [reads the book])
  SIZER   risk_sizer         target signals + equity + prices -> target positions
                             (applies the stop, risk budget, max-names cap)
  RECON   order_generator    target positions - current positions -> orders
                             (stable idempotent order ids; no-trade band; cash check;
                              near-level flags for the brief)
  FILL    paper_broker       orders + prices -> fills (idempotent; slippage + cost model)
  BOOK    portfolio_updater  fills + current book -> new book + per-ticker decision trace

Sinks:
  ledger_writer  — append fills to the immutable ledger, then persist the positions snapshot (atomic)
  brief          — today's action list: holdings, what changed, orders + why, near-stops, P&L

Wiring:
  current_book -> EXITS, SIZER, RECON, BOOK
  market_today -> MKT -> SIGNAL -> EXITS -> SIZER -> RECON -> FILL -> BOOK -> ledger_writer, brief
  market_today also feeds EXITS (market-defined stops), FILL (fill prices), brief (marks)
```

The backtester compares *many* strategy variants; execution commits to *one*
(or a chosen ensemble). Switching the live strategy is a deliberate, logged event.

## Locked decisions

### 1. The book is an event-sourced ledger; the snapshot is derived

The immutable, append-only **trade ledger** (every fill, ever) is the source of
truth. Current positions, cash, open lots, and realized P&L are a *derived*
snapshot that can always be rebuilt by replaying the ledger. Constraint that falls
out of this and must be honored: **nothing in the book that isn't derivable from
the ledger** — if a value can't be reconstructed from the log, the model has a
hole. Corrections are new **compensating events**, never edits to past entries;
the log is append-only.

### 2. The consistency invariant, and its failure policy

The book must satisfy `snapshot == replay(ledger)` — literally the
checkpoint-consistency invariant from recovery theory (a snapshot must equal the
state obtained by replaying the log). It is checked at **both** run boundaries:

- **Run start:** replay the ledger and confirm the loaded snapshot matches —
  catches a corrupted or stale book *before* trading on it.
- **Run end:** after appending today's fills and rewriting the snapshot, confirm
  it matches again — catches a bug in today's update path.

Failure policy — *heal-in, fail-stop-out*:

- A **start-of-run** mismatch means the snapshot drifted; rebuild it from the
  ledger (the ledger is truth) and warn loudly.
- An **end-of-run** mismatch means the update logic just produced an inconsistent
  book; **halt and refuse to commit** rather than trade on it.

### 3. Timing: decide at close t-1, fill at open t

The decision uses only data available at decision time (no look-ahead). The
convention is: **decide on the close of day t-1, fill at the open of day t**, on a
shared trading calendar, with the decided-on prices **snapshotted into the
ledger** (adjusted price series get retroactively revised, so last night's close
is not guaranteed to equal the value re-fetched later; snapshotting keeps
decisions reproducible).

The backtester must use the **identical** convention so live is provably
consistent with the backtest. The current backtester is *close-fill* (it holds
`signal[t-1]` over a close-to-close return); moving it to fill-at-next-open is the
one change that alters its return math and shifts its numbers slightly (the
overnight gaps on entries and exits). This is the honest convention anyway — you
cannot trade at a close you are still computing from — so both offices move up to
it rather than the backtester being distorted. **Sequencing:** make the current
convention explicit in the backtester's docs now; make the actual switch as part
of building this app, then re-baseline and re-verify both together, so the
in-flight tester round is not churned.

### 4. Backtest-live consistency is the trust bridge

Live is only trustworthy if it does what the backtest said. So the strategy, the
sizing/stop rules, the cost model, the trading calendar, and the no-look-ahead lag
must be **shared definitions both offices import**, not re-implemented per office.
"Make the backtester compatible" is mostly this *factoring* (lift the shared policy
into one place) plus the fill-convention change in §3. Divergence here is the
biggest silent-failure risk in the whole app.

### 5. Exactly-once execution via idempotent order ids

Every order carries a deterministic id (`{trade_date}:{ticker}:{intent}`). The
paper broker records filled ids and treats a duplicate as a no-op, so running the
same day twice produces the same book. **Commit point:** appending fills to the
ledger. Order of operations: decide → append fills to ledger (commit) → write
positions snapshot → emit brief. Never write positions before the fills are
durable; if the run dies between the two, the next run rebuilds positions from the
ledger and is consistent.

### 6. Observability: a decision trace, not just orders

For each ticker each day, record signal value → target → order → the rule that
fired, alongside the fill. That trace is what answers "why did we exit NVDA?" in
plain English (Cowork reads the ledger + trace + book) and what makes "what's near
a stop" and "what changed since yesterday" cheap. The brief is a rendering of the
trace plus the book — state, not statistics — which is exactly the shape this
question wants.

### 7. Determinism and the run receipt

The decision path is deterministic: same book + same market data + same params →
same orders, no wall-clock or randomness, so re-runs are idempotent and any day's
decision is reproducible. Each day's ledger entry and brief stamps the strategy,
params, stop, cost, and prices-as-of that produced it — the run-settings receipt
idea from the backtester, carried into the ledger.

### 8. Exit policy is a pluggable, disclosed option (and the one book-dependent seam)

Signals are **book-independent by default**: `SIGNAL` computes a target from
market data alone, and all account-awareness — sizing, portfolio caps, rebalance
bands, capital budgeting — lives downstream in `SIZER`/`RECON`, which take the
book. That purity is what makes the signal roles reusable across both offices,
testable, and trivially backtest-consistent.

The one genuinely book-dependent decision is **exits/stops keyed to your realized
entry** (a stop below the price you actually filled at, a trailing stop from your
own high-water mark, pyramiding from your entry). Rather than hardwire this in or
omit it, it is a **pluggable, shared, disclosed exit policy** — a sibling of the
strategy, the sizing rule, and the cost model — selected by the trader, stamped
into the receipt/ledger, and imported by both offices so backtest and live use the
same one. It occupies the optional `EXITS` slot between `SIGNAL` and `SIZER`;
`SIZER`, `RECON`, and `BOOK` are untouched, and the `market_today -> SIGNAL` edge
stays pure.

Two implementations:

- **Market-defined (default):** stops computed from prices (e.g. ATR / Donchian),
  book-independent; backtest and live match by construction. `EXITS` does not read
  the book — effectively a pass-through on account state.
- **Realized-entry (opt-in):** `EXITS` reads the book's entry and high-water mark
  and can force a close or trim. Faithful to how risk is actually managed, but
  **gated on the fill-modeling backtester (§3)**: it only stays backtest-consistent
  once the backtester models fills and therefore has a realized entry to stop
  against. Until then, the app should refuse or warn if realized-entry exits are
  selected against a close-fill backtester, rather than let live silently diverge
  from what was tested — the same discipline as the §2 invariant.

Build discipline (as with threads-vs-processes): design the `EXITS` seam now, ship
the market-defined default first, defer building the realized-entry policy until
it is wanted, and keep the policy set small (two, not a zoo) to bound the
backtest-vs-live consistency surface.

## Resolved in the open-items pass

- **Catch-up policy.** On missed runs (laptop off, scheduling gap), process each
  missed trading day **in order** so the book stays continuous — a gap silently
  changes what the strategy would have done.
- **Fill-price model.** Fill at the **open**, adjusted by the **shared** cost /
  slippage model (same bps as the backtester), applied at that same open fill.
  "Reuse exactly" means the identical policy applied at the identical point, which
  is precisely what the §3 fill-convention change makes possible.
- **No-trade band (churn control).** A minimum position delta worth trading is a
  **shared, disclosed** parameter applied in **both** offices — never an
  execution-only tweak — so live turnover and cost match the backtest. Signal-level
  churn control (smoothing, hysteresis via dual windows) lives in the strategy and
  is therefore already shared; the band is the execution-level backstop for
  rounding noise. Both are stamped in the receipt. (Standard practice: the no-trade
  region is the provably optimal policy under proportional transaction costs.)
- **Multiple strategies = independent processes.** To run several strategies, run
  **one office per strategy, each as its own independent OS process with its own
  book / ledger directory** — completely independent, no messages between them, no
  shared capital, no cross-strategy constraints. This is the *easy* use of
  processes (isolation and independent restart with no cross-process coordination —
  no distributed snapshot or termination detection needed), available now without
  the deferred work of splitting a single office across processes. Independence is
  exactly right for **comparison** (each strategy judged on its own); a single
  shared-capital combined portfolio is a different, coordinated problem,
  deliberately out of scope. MVP is one strategy / one book; the book carries a
  strategy tag (here, simply its own directory) from day one, so several books is
  configuration, not migration.
- **Supervisor and aggregator live outside the framework.** The office owns the
  correctness-critical core (idempotent daily transaction, checkpointed book,
  structured output files); orchestration and analysis sit on top of those output
  files and are not agents or offices.
  - *Aggregator* (compare the live books) is **user-specific** — different users
    rank by return, Sharpe, drawdown, R — so it is **not shipped**: a README line
    tells the user she can point Cowork at the book files and have it build
    whatever comparison she wants.
  - *Supervisor* (launch one scheduled run per strategy, re-run on failure) is
    **common-shaped and correctness-adjacent** (liveness — don't silently skip a
    trading day), so ship a **tiny worked example**: one independent process per
    strategy pointed at its own book directory, safe-to-re-run (catch-up handles
    gaps), and a minimal "did the book advance today?" check. Deliberately trivial —
    it leans entirely on the office's per-run guarantees — and kept as an
    example / recipe, never framework core.

  General rule this sets for every app: **mention the parts that are user-specific
  and safe to freeform; ship a tiny example of the parts that are common-shaped or
  correctness-adjacent; keep the tested core small.**

## Still open

- **Ledger schema:** the exact event record — complete enough to satisfy the §1
  derivability constraint (every book field reconstructable from the log) and to
  carry the strategy tag, the prices-as-of, and the order id.
- **Slippage magnitude:** the actual bps for the shared cost / slippage model —
  the *mechanism* is settled; the number is a parameter to choose and disclose.

## Known simplification

Corporate actions: using split/dividend-adjusted price series (as the backtester
does) sidesteps most split/dividend accounting for a paper book. Note it as a
known limitation rather than building real corporate-action handling now.

## Why this is also the course's best example

Almost every hard idea in a distributed-systems course is load-bearing here, not
decoration: the event-sourced log and the `snapshot == replay(log)` invariant
(checkpoint consistency), the daily run as a transaction with a defined commit
point, heal-in vs fail-stop-out recovery, idempotency and exactly-once under
crash-restart, and no-look-ahead / as-of correctness. The later thread-to-process
migration then becomes a live lesson: the same office, split across processes,
with the message-only discipline making it a transport swap rather than a rewrite.
