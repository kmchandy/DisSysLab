# mac_speed_suite — Phase 2 design

*From return-series stats to trade-level truth. Design doc for review; no code
written yet. Last updated 2026-08-12. Driven by the trader's second round of feedback
(logged verbatim in `TESTER_FEEDBACK.md`, 2026-08-12).*

## Where Phase 1 landed, and what the trader is now telling us

Phase 1 built the research-grade trust layer: one report, relative strength,
transaction costs, and — the big one — **out-of-sample validation and Monte
Carlo robustness, on by default** (now a single `validation_gate` that runs both
in one pass). Two of the trader's five new asks are therefore *already shipped*:

- **"Out-of-sample by default, not a flag."** Done. The default run ranks by
  out-of-sample performance. His hand-done 50/50 experiment — the current winner
  falling 2nd → 10th while an unmentioned variant was 1st in both halves — is
  exactly the failure walk-forward exists to catch. We should say so.
- **"Costs as a dial, with turnover shown."** The dial is done (`cost_bps` is a
  settable parameter, default 5); turnover is computed. What's missing is
  *surfacing* turnover in the report, and (optional, deferred) a cost-sensitivity
  sweep. The trader himself deprioritizes this.

The rest of his feedback is one deep reframe plus its consequences.

### The reframe: we measure the wrong *unit*

Every number in today's table is a property of a **daily return series** (Sharpe,
annualized return, drawdown). A trading decision needs properties of **trades**:
how many, how long held, win rate, average winner vs average loser, worst single
trade, expectancy. "Twenty trades and two hundred can produce an identical Sharpe
and mean completely different things, and right now I can't tell them apart." He
is right, and this is the same gap that let a strategy which never opened a
position still get a row: we never counted trades, so nothing could say "zero."

Everything below follows from taking the *trade* — not the day — as the unit.

## Workstreams

Lettered continuing from Phase 1 (A–D). Each is tagged with what kind of change
it is, because Mani asked and it matters for sequencing.

### E. Trade-level metrics — CORE, the big gap  *(new computation + display)*

**Not** a display-only change. Today the backtester emits a per-day return series
per ticker. We add one pass that walks the position series each ticker already
produces inside the backtester loop and segments it into discrete **trades** — a
trade is a contiguous in-market run: it opens when the position goes from flat to
in-market and closes when it returns to flat (or the window ends, which marks an
*open* trade). For each trade we record entry date, exit date, hold length (bars),
and trade return (the compounded daily return over the hold). From that one list,
all of the trader's numbers fall out:

- trade **count**, average **hold**, **win rate** (fraction with positive return),
- **average win** and **average loss**, **worst single trade**,
- **expectancy** = win_rate × avg_win + loss_rate × avg_loss,
- **RR** (reward:risk) = avg_win / |avg_loss|.

Two consequences worth calling out:

- **The zero-trade row becomes honest.** A strategy with 0 trades shows "0
  trades" and is excluded from (or clearly flagged in) the ranking, instead of
  silently occupying a row. This *fixes the root cause*, not the symptom.
- **"If a number is built on twelve trades I want to see the twelve."** We expose
  a per-strategy **trade list** (a drill-down: the twelve rows, each with entry,
  exit, hold, return). Cheap once the trade list exists — it *is* the underlying
  data.

Why it's contained: no new pipeline stages, no new source data. The positions are
already computed in the loop that tracks turnover; we add a derivation and carry a
`per_ticker_trades` structure alongside the existing `per_ticker_returns`.

### F. Honest out-of-sample presentation — DISPLAY-ONLY

Purely rendering; the numbers already exist (`is_sharpe`, `oos_sharpe`,
`ranked_by_oos`, turnover). We stage the contrast the way a trader reads it:

- **Pick-vs-outcome.** Show, side by side, the variant you *would have picked* on
  the in-sample half and where that pick *actually ranked* out-of-sample — the
  "2nd → 10th" movement made explicit next to the ranking, not implied.
- **"Consistent in both halves" flag.** Mark variants that rank near the top
  in-sample *and* out-of-sample (the quiet variant that wins both is the one worth
  trusting). This is the signal the trader found by hand.
- **Turnover in the table.** Put turnover next to each row so the activity level
  is visible where the return is.

### G. R-multiple sizing — HIGH VALUE, depends on E  *(new modeling assumption)*

Trade-level by nature, so it sequences *after* E. Today we account in constant
notional (±1 unit) and report annualized return. The trader wants **R multiples**:
risk a fixed amount per trade, let the distance to the stop set the size, and
report outcomes as multiples of that risk — "made 14R over 60 trades, average
winner 2.1R, average loser −0.8R."

**Definitions.** For a trade, *initial risk* = distance from entry price to the
stop, in price terms (that distance is 1R). Position size is chosen so hitting the
stop loses a fixed budget, so `size = risk_budget / (entry − stop)`. The trade's
result in R is:

```
R = (exit_price − entry_price) / (entry_price − stop_price)      # for a long
```

*Worked example.* Enter at 100, stop at 96 → 1R = \$4/share. Exit at 110 →
(110−100)/(100−96) = **+2.5R**. Stopped at 96 → **−1R**. A \$4 move in a \$100
name and a \$0.40 move in a \$10 name can both be 1R, so R multiples are directly
comparable across stocks of different price and volatility — which annualized
return on constant notional is not. It is also the language traders use.

**What we must add: a stop rule (a disclosed assumption).** We have no stops
today. Default to a volatility stop: `stop = entry − k·ATR(n)`, where ATR (average
true range) is computed causally from the OHLC we already have, so
`initial_risk = k·ATR(n)` at entry. `k` (e.g. 2) and `n` (e.g. 14) are surfaced
through the same "here's what I assumed you meant" loop and are user-changeable.

**MVP vs full.** MVP: keep the existing portfolio equity curve, and *additionally*
report each trade in R (per-trade R, expectancy in R, total R). This is additive —
R accounting sits on top of the trade list from E without rebuilding portfolio
aggregation. Full (later): a genuinely R-sized equity curve where each position is
sized to a fixed risk budget, replacing constant notional as the primary lens.

### H. Cost sensitivity — DEFERRED  *(small; the trader deprioritized)*

"Watch the number move as I turn costs up." A small sweep (result at 0 / 5 / 10 /
20 bps) is more convincing than one figure. Explicitly deferred: the dial and
turnover already exist; this is a nice-to-have the trader told us to skip for now.

## The second app: "what do I hold tomorrow" — SEPARATE OFFICE, scoped not built

The trader: *"I'd want that, but it's a different app."* We agree, and it fits the
framework rather than fighting it. "Is this strategy any good?" wants history,
statistics, and out-of-sample discipline (this app). "Given what I hold, what do I
do tomorrow?" wants today's state — current positions, what changed since
yesterday, what's near a level — and almost no statistics. Serving both from one
table makes both worse.

In DisSysLab terms this is a **second office** that *reuses the same signal-
computer roles* (the reuse contract pays off here) but swaps:

- **source:** today's bars + the user's current positions (not 10 years of CSV),
- **sinks:** a watchlist / action list ("hold, add, exit, near stop") — not a
  stats report.

This is strong framework and paper material: the same roles recomposed for a live
decision instead of a backtest, and a clean illustration that the office, not the
app, is the unit of reuse. Phase 1's doc already earmarked a "daily live-operating
office" as future work; this is that, scoped by the trader's separation-of-questions
argument. **Out of scope for Phase 2 build; tracked here as the next office.**

## Files: new vs edited vs untouched (anticipated)

- **Edited — `roles/_backtester_core.py`:** add trade segmentation; emit
  `per_ticker_trades` (entry/exit/hold/return, open-trade flag). For G, compute
  ATR and per-trade R.
- **Edited — `roles/evaluator.py`:** aggregate trade stats per strategy
  (count, hold, win rate, avg win/loss, worst, expectancy, RR; R aggregates for
  G); mark zero-trade strategies.
- **Edited — `sinks/report_html_sink.py`:** trade-stats columns next to the
  table; the per-strategy trade-list drill-down; the pick-vs-outcome and
  consistent-in-both-halves presentation (F); turnover column.
- **Untouched:** the pipeline wiring, the gate/comparator loop, the signal
  contract. Strategies still declare one `compute_variant_signal`; trades are
  derived downstream, so no strategy needs to know about trades or R.
- **New tests:** trade segmentation (incl. open trade at window end, zero-trade
  strategy, single-bar trade), expectancy/RR math, R computation on the worked
  example, and a report-render smoke test.

## Build order

1. **E — trade-level metrics** (biggest gap; unblocks everything; fixes the
   zero-trade row at its root). Ship with the trade-list drill-down.
2. **F — honest OOS presentation** (display-only; fast; high perceived value).
   Can land in parallel with E since it touches only the sink.
3. **G — R multiples, MVP** (per-trade R on top of E's trade list; stop as a
   disclosed assumption).
4. **G — full R-sized equity curve**, if the trader wants R as the primary lens.
5. **H — cost sensitivity**, only if asked.
6. **Second office** — separate design doc when we pick it up.

## Open decisions / config knobs

- **Trade definition with scaling.** MVP treats any nonzero position as "in" and a
  trade as a contiguous in-market run. Scaling in/out (position size changing
  mid-trade) is a later refinement — do we need it for these long-only trend
  rules, or defer?
- **Open trade at window end.** Report it as an open trade with mark-to-market
  return, excluded from win/loss stats? (Proposed: yes, shown separately.)
- **Stop convention for R (G).** ATR multiple `k` and lookback `n` defaults, and
  whether some strategies (e.g. Turtle) should use their *own* native stop instead
  of a common ATR stop.
- **Primary unit.** Do we keep annualized return as the headline with R alongside,
  or make R the headline once G lands? (the trader prefers R.)
- **Ranking with mixed trade counts.** How to rank a 12-trade strategy against a
  200-trade one — flag low-sample strategies rather than hide them?
