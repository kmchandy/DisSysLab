# mac_speed_suite — Phase 1 design

*A backtester a small trading firm would actually use. Design doc for review;
no code written yet. Last updated 2026-08-11.*

## Goal and audience

Turn the existing `mac_speed_suite` batch backtester into something the trader — and a
four-person firm — would use for **research**: express strategies naturally
(including relative strength), trust the results (out-of-sample validation and
robustness), and see honest comparisons. The goal is not to beat a big firm's
console; it is to be the smallest thing a small firm keeps and returns to.

Audience for the *app*: a finance-literate, Python-comfortable user (the trader). The
step-by-step first-year tutorial is a separate deliverable.

Phase 1 is the **research-grade layer**. The **daily live-operating office**
(pull bars, propose trades, checkpointed paper book, morning brief, decay
alerts, English explanations) is Phase 2 and is out of scope here.

## What exists today (the seams we build on)

Pipeline as wired in `office.md`:

```
csv_stock_history  ->  MAC / DONCHIAN / TURTLE signal computers
                   ->  9 backtesters (one per variant)
                   ->  JOIN (synchronizer)
                   ->  EVALUATOR
                   ->  console_printer            (+ a separate make_report.py)
```

**Reuse contract (must be preserved).** A strategy is exactly one compute
function `compute_variant_signal(bars, params) -> List[float]` — a per-day
position size, causal (no look-ahead). Everything downstream is shared and
strategy-agnostic. Adding a strategy = one role file + a few lines of
`office.md`. Confirmed by reading `_signal_common.py`, `_backtester_core.py`,
and `evaluator.py`.

Facts confirmed in the code that shape this design:

- The data source already supports `start`/`end` date filtering — the
  out-of-sample split really is "one line of config."
- `make_report.py` re-implements the pipeline with the three families
  hardcoded, so `report.html` and `dsl run` are two independent definitions of
  "what strategies exist." **This is bug item 2.**
- A flat (never-entered) strategy produces an all-zero return series
  mathematically identical to a traded-to-zero one — the evaluator can't tell
  them apart. **This is bug item 3.**

## Workstreams

### A. One report, one truth  (fixes item 2) — CORE

Promote report generation into an office **sink** (`report_html`), fed by the
evaluator's (later the comparator's) real message. It derives the strategy list
and labels from the message itself (`variants` / `ranked`), so it can never
disagree with `dsl run`, including any strategy the trader just added. Retire
`make_report.py`'s private pipeline. **This is the foundation — built first —**
because relative strength and the trust layer all write to the report.

### B. "Never traded" is visible  (fixes item 3) — CORE

The backtester already holds each day's signal, so it emits two cheap per-ticker
numbers alongside `per_ticker_returns`: `days_in_market` (days with a non-zero
position) and `turnover` (count of position changes). The evaluator carries
them; the report shows "no trades" as a distinct state, not a flat row that
looks like a loss. No downstream contract change.

### C. Relative strength  (the trader's wall) — CORE, the headline unblocker

The one real architectural addition, designed to keep the per-ticker contract
intact:

- **New shared worker `market_context`**, inserted between the source and the
  three signal computers. It adds, computed **causally** (only data up to day
  *t*, so the no-look-ahead check still applies): a `market` benchmark return
  series (equal-weight of the basket = "your peers"; a real index ticker such as
  SPY is a one-CSV drop-in later) and, per date, each ticker's cross-sectional
  `rank` / relative strength. It passes everything else through unchanged.
- **Extend `make_signal_computer`** so a compute function can *optionally* take
  the context: `compute_variant_signal(bars, params, context=None)`, decided via
  `inspect.signature`. MAC / Donchian / Turtle stay **byte-for-byte unchanged**
  because they still take `(bars, params)`.
- **New example strategy `rs_trend.py`**: long only when the stock's own trend is
  up *and* its relative-strength rank is in the top half of the basket — exactly
  the sentence the trader couldn't express. Because the context carries each ticker's
  rank, "hold the top N" becomes a one-line per-ticker test, so the
  joint-selection case falls out for free.
- Backtester and evaluator are **untouched** — they never learn any of this
  exists.

### D. Trust layer

Why it exists: ranking many variants on one window and bolding a winner is how
you pick the luckiest, not the best. This layer answers "is the edge real, and
how fragile is it?"

- **D1. Transaction costs — CORE.** The backtester charges a cost on `turnover`
  (basis points per unit of position change). Kills the 0%-cost fantasy the trader
  flagged and penalizes over-trading. Deterministic; a `cost_bps` parameter.
- **D2. Strategy correlation matrix — CORE.** The evaluator emits the
  correlation matrix of the variants' portfolio return series; the report shows
  it. Answers the trader's "are my 'different' strategies secretly the same bet?"
- **D3. Out-of-sample validation with walk-forward — CORE, required.** The
  single hold-out is just the one-fold case; the full walk-forward schedule is
  in scope for the app. Detailed below.
- **D4. Monte Carlo robustness — small increment on D3.** Same pipeline and same
  gate/comparator loop; only the input data changes (resampled histories instead
  of time slices). Detailed below.

## Out-of-sample validation, in detail

### What "train" and "test" mean

If you rank a dozen variants on one stretch of history and bold the winner, you
have very likely picked the luckiest, not the best — the trader's rule fell from #2 to
#10 on the second half of the same data. So you hold data back. Rank the variants
on an earlier **in-sample (train)** stretch, then measure how those *same*
variants do on a later **out-of-sample (test)** stretch that had no part in
choosing them. If the in-sample winner stays strong out-of-sample, trust it
more; if it collapses, it was noise.

Note the specific flavor of overfitting here: we are not fitting continuous
parameters, we are **selecting among a fixed menu by ranking**. That selection
is itself the overfit — picking the best of twelve on one window. The train/test
split checks whether the selection survives.

### How to split 10 years

**Single hold-out (the intuition).** Rank on 2016–2022, then measure those
variants on 2023–2025. One split, easy to explain.

One split is arbitrary — a 2022 test year (crash) and a 2017 test year (calm)
give opposite verdicts — and it wastes data. So the honest version is
**walk-forward**: roll the split forward and stitch the out-of-sample pieces
together.

Expanding-window walk-forward on 2016–2025:

| Fold | Train (in-sample, used to rank) | Test (out-of-sample, scored) |
|------|----------------------------------|------------------------------|
| 1    | 2016–2021                        | 2022                         |
| 2    | 2016–2022                        | 2023                         |
| 3    | 2016–2023                        | 2024                         |
| 4    | 2016–2024                        | 2025                         |

Concatenate the four test years and you have an out-of-sample track record in
which every day was judged on data not used to pick the strategy. **Rolling
window** is the same idea with a fixed-length train span (e.g. always the last
five years) instead of an expanding one. The office reads the schedule as
config; the tutorial default is a simple expanding walk-forward with one-year
test folds.

### The loop — mapped to the debate office

We do this **inside the office** as a feedback loop, not as an external script
that runs the office twice. The debate office is the template:

- Debate: `starter` -> `Sasha` (a **gate** holding the problem bank) -> three
  panellists -> `Sync` (join) -> `Riley` (moderator). Riley's `finish` outbox
  loops back to `Sasha` to release the next problem; the gate terminates when the
  bank is exhausted.
- Walk-forward: `csv_stock_history` loads the full span once and feeds a **window
  gate** (the Sasha analog) holding the list of **labeled spans**
  `[(fold1, train), (fold1, test), (fold2, train), ...]`. It releases one span at
  a time — slicing the history to that span and stamping it with its `fold` and
  `role` — into the **unchanged** pipeline. The evaluator's result flows to a
  **comparator** (the Riley analog), which accumulates results, groups them by
  fold, and signals the gate to release the next span (the feedback edge). When
  the bank is exhausted, the comparator computes the degradation scorecard
  (train vs test Sharpe, rank stability, which in-sample winners survived) and
  emits it to the report sink; the gate terminates and termination detection
  closes the office.

Key points:

- A single hold-out is just **one fold = two spans**; walk-forward is **N
  folds**. Same machine, longer bank.
- Per fold we run the pipeline on the train span (to get the ranking) *and* the
  test span (to score the winners) — that is why both are in the bank.
- The `fold` / `role` tag rides on the message so the comparator can group.
- Everything between the gate and the comparator is unchanged, so even the
  walk-forward feature preserves the reuse contract. New roles: `window_gate`,
  `comparator`.
- Because it is one office, it is one `dsl run`, one termination, one
  checkpointable computation — you can checkpoint between folds and resume
  mid-walk-forward — and Cowork can explain the loop in English.

## Monte Carlo — a small increment, not a second effort

Train/test asks "does the edge survive on data I did not select on?"
(overfitting). Monte Carlo asks "how much of this result is luck, and how fragile
is it?" — it produces a *distribution* of outcomes instead of one number: "the
backtest made 15% with a 20% drawdown, but a bad-luck path loses 8% and could
have drawn down 35%," plus the probability of a losing year and confidence bands.

**The key point: the backtest pipeline is unchanged — only the input data
changes.** If we generate Monte Carlo samples by *resampling the input price
history* (a block bootstrap, below), then a Monte Carlo run is structurally
identical to a walk-forward run: the gate feeds a different input dataset into
the same unchanged `market_context -> signals -> backtest -> evaluate` pipeline,
and the comparator aggregates the outcomes. Walk-forward and Monte Carlo are
**the same machine with a different bank**:

- Walk-forward bank: a list of real-history **time slices** (train/test folds).
- Monte Carlo bank: a list of **resampled histories** (seeded), same message
  shape.

So if the gate is designed generically — "hold a list of input datasets and
release them one at a time" — Monte Carlo mostly falls out of walk-forward.

**What is genuinely new for Monte Carlo, on top of a built walk-forward:**

1. A seeded **resampler** that turns the one real history into K synthetic ones.
   Use a **block bootstrap across dates for the whole panel at once** (resample
   blocks of consecutive days, the *same* days for every ticker) so short-run
   autocorrelation *and* the cross-section — which relative strength depends on —
   are preserved. This is the one substantive new function.
2. A **distribution mode** in the comparator: instead of a train-vs-test
   comparison, collect each run's outcome metrics and report percentiles,
   probability of loss, and confidence bands.
3. A **report section** for the distribution (bands / percentiles).

Everything else — the source, the pipeline, the gate loop, termination, the
report plumbing — is reused. Estimated incremental effort once walk-forward
exists: **roughly a day or two**, dominated by the resampler and the distribution
aggregation.

**The one real difference from walk-forward is run count.** Walk-forward is a
handful of folds; a Monte Carlo distribution wants many samples (commonly
500–2000). The pipeline is cheap here (5 tickers, ~1 year, a handful of
variants), so even ~1000 passes is seconds-to-minutes — but it is the one place
compute grows, and in practice you would run Monte Carlo on the *selected*
strategies, not all variants. Seed the resampler so the whole distribution is
reproducible (still deterministic and testable).

*Cheaper alternative, for reference:* reshuffling the strategy's **output** daily
returns (rather than resampling input prices) needs no pipeline re-run at all,
but it operates on the evaluator's output — a different seam that does **not**
reuse the loop — and only tests path/sequence risk on the same returns rather
than alternative market histories. The input-resampling version above is
preferred precisely because it reuses the walk-forward machine.

## Files: new vs edited vs untouched

**New:** `roles/market_context.py`, `roles/rs_trend.py`, the `report_html` sink,
`roles/window_gate.py`, `roles/comparator.py`, and (stretch)
`roles/monte_carlo.py`.

**Edited:** `_signal_common.py` (optional `context` arg),
`_backtester_core.py` (turnover, `days_in_market`, `cost_bps`), `evaluator.py`
(carry the trade counts, add the correlation matrix), `office.md` (insert the
context stage, add `rs_trend`, swap in the `report_html` sink, add the
gate/comparator loop).

**Untouched by design:** the strategies the trader already has (MAC/Donchian/Turtle),
and the core backtester/evaluator math and message contract.

## Build order

1. Report sink (A) — the foundation everything writes to.
2. Never-traded (B) — small, honesty-critical.
3. Relative strength (C) — the unblocker; get it into the trader's hands here.
4. Transaction costs (D1) + correlation matrix (D2).
5. Out-of-sample loop (D3): single hold-out first, then the full walk-forward
   schedule. **Build the gate generically here** — "hold a list of input
   datasets" — so Monte Carlo is a small increment rather than a rebuild.
6. Monte Carlo (D4): same loop, resampled input. Roughly a day or two on top of
   step 5.

## Open config knobs / decisions

- **Walk-forward schedule:** expanding vs rolling; train/test lengths; number of
  folds. Default: expanding, one-year test folds.
- **"Market" benchmark:** basket equal-weight (default) vs a real index ticker
  (CSV drop-in).
- **Cost level** (basis points).
- **Monte Carlo:** number of resamples, seed, method (plain return bootstrap vs
  block bootstrap to preserve short-run autocorrelation).
