# paper_trader — deferred backlog

Ordered by when it makes sense to do it, not strict priority. Nothing here blocks
a first `dsl run .`; these are the follow-ons after the MVP office runs.

## A. Backtester consistency pass (the §4 shared-definitions work)

Do these **together**, bundled with re-baselining the backtester, and **not**
during the in-flight tester round (each shifts the backtester's numbers). Goal:
live is provably consistent with the backtest because both import the *same*
definitions.

1. **Fill convention** — move the backtester from close-fill to
   decide-at-close/fill-at-next-open (matches the paper trader; also enables
   realized-entry exits).
2. **No-trade band** — apply the same band in the backtester so turnover/cost
   match live.
3. **Sizing** — factor the backtester's inline inverse-vol weighting into the
   shared sizing module (`risk_sizer`), imported by both.
4. **Strategy** — unify the paper trader's `strategies.py` (currently a
   duplicated `mac`) with the backtester's signal compute into one shared module.

## A2. Share the strategy self-check with the backtester

`strategy_selfcheck.py` (the Tier-3 look-ahead / contract / determinism guard) is
pure and app-agnostic. It currently lives with the paper trader; fold the same
"offer the self-check on any generated strategy" step into the
`backtest-strategy-builder` skill so a strategy is checked at *invention* time,
before its first backtest — not just before its first paper trade. When A.4
unifies the strategy module, the self-check moves next to it and both skills
import one copy.

## B. Context / relative-strength strategies

The MVP supports per-ticker strategies only (`compute_fn(bars) -> signal`).
Relative strength needs the daily cross-section. Thread market context through
`market_view.as_of_view` so context-dependent strategies (rs_trend) run in the
execution app too.

## C. Realized-entry exits

Build the book-reading `EXITS` policy (stops keyed to the actual entry /
high-water mark). Gated on A.1 (the fill-modeling backtester); until then it
raises on purpose so live can't silently diverge from the backtest.

## D. Brief enhancements

- Near-stops (names close to a stop level) once stop levels are modeled.
- Day-over-day P&L attribution (currently: equity + cumulative P&L only).

## E. Operations

- The tiny **supervisor** example: one scheduled `dsl run .` per book, re-run on
  failure, a "did the book advance today?" liveness check. Kept as an example,
  not framework core.
- Multi-book comparison: leave the **aggregator** out; a README line telling the
  user to point Cowork at the ledgers.

## F. Sizing / R

- `risk_based` sizing is built and opt-in. A full R-sized equity curve (each
  position sized to a fixed risk budget as the primary lens) is a later option,
  never a default.

## G. Repo / thesis (after the paper trader is runnable)

- `THESIS.md` (the modest claim: a Cowork skill over a tested library is a good
  way to surface apps, especially for distributed systems).
- A "surfaced apps" index and a first-class **correctness** section (tests +
  proofs) — the claim rests on the substrate being provably correct.
- Package the `paper-trader` skill as a `.skill`.

## H. Next app (after the paper trader reaches the domain experts)

- The drug-discovery compound-triage office — the same office shape (screen many
  items in parallel by several criteria → synchronize → rank → report), proving
  "different domain, one distributed pattern."
