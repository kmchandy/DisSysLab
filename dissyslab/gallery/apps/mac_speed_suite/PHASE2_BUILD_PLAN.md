# mac_speed_suite — Phase 2 build plan

*Execution plan for the backtesting app. Companion to `PHASE2_DESIGN.md` (the
what/why) — this is the how/when, plus the two decisions we locked. Last updated
2026-08-12.*

## What we're building, and for whom

A backtesting framework that two domain experts (Sebu, Vikram) drive entirely in
English: **they describe strategies and set parameters by talking to Cowork;
everything else — implementation, wiring, validation, reporting — is done for
them.** This is the worked example of the project thesis: a tested library
(DisSysLab functions + OfficeSpeak prompts + the `.skill`) added to Cowork lets a
non-programmer build and tune a real, trustworthy app in English, without
re-synthesising the hard, error-prone distributed substrate each time.

## Two decisions (locked)

**1. The parameter interface is conversational, with a settings receipt.** Sebu
and Vikram set parameters by talking to Cowork ("use these eight stocks, five
years, 500 Monte Carlo samples, a 2×ATR stop") — the strongest showcase of Cowork
itself, and no form to maintain. They never edit a settings file by hand. But
every run **records the exact parameters it used** as a receipt — stamped into the
top of `report.html` and kept in a plain settings file Cowork maintains — so any
result is reproducible and citable (which stocks, what window, how many samples,
which stop produced *this* report). Conversation is the front door; the receipt
is provenance.

**2. R is shown alongside, not imposed.** Guiding principle: *give traders a
framework, don't tell them how to trade.* Full risk-sizing (sizing every position
to a fixed risk budget) is itself a trading methodology, so it is **not** the
default. R multiples, expectancy-in-R, and the trade stats are shown next to the
existing numbers (annualized return stays the headline) as one more comparable
lens. Computing R needs a stop, and a stop is a choice we won't impose either, so
the stop is a **disclosed, user-settable knob** (default ATR × k; changeable in
English, e.g. "what does this look like with a tighter stop?"). Full risk-sizing
stays available as something a trader can *invoke* later — an option they reach
for, never a default handed to them.

## Status (2026-08-13)

Built and committed, all tests green: step 1 (conversational params + run-settings
receipt), E (trade-level metrics + drill-down + zero-trade fix), F (honest
out-of-sample presentation), G (R multiples via a disclosed stop). Remaining
before the next tester round: L1 expressiveness gaps as they arise, and the
acceptance corpus (L3). The conversational interface examples live in
`skill_for_testers/COWORK_EXAMPLES.md`.

## Build order (roughly two weeks, feedback-driven)

1. **Conversational parameter layer + settings receipt.** Consolidate the tunable
   knobs (basket, history length, Monte Carlo samples, walk-forward folds, cost
   in bps; R-stop knobs added in step 4) into one clearly-labeled place the office
   already reads, and make each run stamp the parameters it used into the report
   (and a settings file). Update the skill so Cowork can set any knob in English
   and echo the settings back. Ships something Sebu/Vikram can poke day one.
2. **E — trade-level metrics** (`PHASE2_DESIGN.md` §E). Trade count, hold, win
   rate, avg win/loss, worst, expectancy, RR, plus the per-strategy trade-list
   drill-down. Fixes the zero-trade-row bug at its root. Biggest gap; unblocks R.
3. **F — honest out-of-sample presentation** (§F). Pick-vs-outcome contrast,
   "consistent in both halves" flag, turnover shown. Display-only; fast; high
   value. Can land alongside E.
4. **G — R multiples (MVP, alongside)** (§G). Per-trade R and expectancy-in-R on
   top of E's trade list, with the ATR stop as a disclosed knob; add the R-stop
   knobs to the settings surface. Completes the parameter list Sebu asked for.
5. **L1 — strategy expressiveness**, driven by the first real Sebu/Vikram
   requests (candidates: short/negative positions, portfolio caps like "at most
   three names," regime filters). Fill gaps they actually hit, not speculatively.
6. **L3/L4 — acceptance corpus + skill/doc updates.** Run ~15–20 real
   strategy-description prompts through the skill as a regression/acceptance
   guard; update the skill and the tester docs to cover R, the trade metrics, and
   the conversational control panel.

## Dependencies and notes

- Step 4 (R knobs) depends on step 2 (trades) and on step 1 (the settings
  surface). Steps 2 and 3 are independent and can proceed in parallel.
- The signal contract (`compute_variant_signal`) stays fixed: trades, R, and the
  receipt are all derived downstream, so no strategy needs to know about any of
  it. Adding a strategy remains one role file + a few `office.md` lines.
- Correctness of the distributed substrate (termination detection, checkpointing,
  the walk-forward feedback loop) is the trust anchor and is *not* regenerated per
  request — it stays in the tested library. Every step ships with regression
  tests; that visible testedness is part of the story, not just hygiene.

## Open decisions still to make (deferred, not blocking)

- Whether the settings receipt lives in `office.md` itself (a labeled SETTINGS
  region) or a separate `settings` file the office and downloader both read.
  Resolved during step 1 once the current wiring is confirmed.
- Ranking strategies with very different trade counts (flag low-sample rather
  than hide) — decided when E lands.
- Whether/when to offer full R-sizing as an invokable option (step 4+).
