---
name: backtest-strategy-builder
description: Adds a new trend-following or backtesting trading strategy to DisSysLab's mac_speed_suite office, following its signal/backtest/evaluate reuse contract, and verifies it before wiring it in. Use this whenever the user wants to add, draft, prototype, or backtest a new trading rule or strategy for mac_speed_suite -- momentum, mean-reversion, RSI, MACD, breakout, moving-average, pairs, or anything similar -- even if they don't say "mac_speed_suite" or "signal computer" by name. Trigger on phrases like "backtest a new strategy", "add a trading rule", "try a momentum strategy on these stocks", "can we test an RSI rule", "what if we added a mean-reversion strategy", or similar requests to try out a new stock-trading idea against historical data. Also use this when the user wants to change a run's parameters in plain English -- which stocks/basket, how far back, how many Monte Carlo samples, walk-forward folds, or transaction cost -- e.g. "use these eight stocks", "run 500 Monte Carlo samples", "test the last five years", "set costs to 10 bps". Requires the DisSysLab repo to be connected/accessible (specifically dissyslab/gallery/apps/mac_speed_suite/).
---

# Adding a strategy to mac_speed_suite

**Skill version: `2026-08-25.d01444c`.** If anyone asks which version of this
skill is loaded, answer with that string, exactly. A skill update can
report success while the old version stays resident.

mac_speed_suite (`dissyslab/gallery/apps/mac_speed_suite/` in the connected
DisSysLab repo) already runs three trend-following strategies -- MAC,
Donchian, and Turtle -- all sharing one BACKTESTER and one EVALUATOR.
Adding a new strategy means writing one new, small piece (a
`compute_variant_signal` function) and letting the existing, already-tested
BACKTESTER/EVALUATOR machinery do everything else. You should not need to
edit `_backtester_core.py`, `evaluator.py`, or `_signal_common.py` to add a
strategy -- if you find yourself wanting to, stop and reconsider (see "When
this doesn't fit," at the end); that usually means the new idea doesn't
actually match this contract.

To change a run's **parameters** (basket, history window, validation, cost) rather than add a strategy, skip to "Setting run parameters" near the end -- that path is a quick edit and a re-run, not the seven steps below.

## Step 1: Read the contract and the three existing examples

Before writing anything, read these files in the connected repo:

- `roles/_signal_common.py` -- the contract itself (VARIANTS, compute
  function, wrapper) and the `make_signal_computer` factory's docstring.
- `roles/mac_signal.py` -- simplest example: stateless, vectorized, always
  fully long or short (+1.0 / -1.0).
- `roles/donchian_signal.py` -- medium: path-dependent (holds a position
  until reversed by an opposite breakout), still +1.0 / -1.0.
- `roles/turtle_signal.py` -- most complex: day-by-day stateful position
  tracking, continuous position sizes (fractions of 1.0), pyramiding.

These three span what the contract supports. Whatever the user describes
almost certainly resembles one of these more than the others -- use that
one as your template rather than starting from a blank page.

## Step 2: Understand what the user actually wants

Ask only what you need to write a real compute function, now including
two questions that used to be skipped and only checked by eye at the end
(Step 6 used to say "a plain direction strategy should be -1/0/1" as
guidance for a human to eyeball -- it's an automated assertion now, which
means it needs an actual declared answer, not a guess after the fact):

- What decides going long vs. short (or how large a position to hold),
  and what data it needs (most technical rules only need OHLCV, which
  `bars` already provides).
- **Is this a "directional" strategy** (always exactly -1.0 / 0.0 / 1.0,
  like MAC or Donchian) **or a "sizing" strategy** (a continuous position
  size within some range, like Turtle's fractional pyramided units)? If
  sizing, what's the declared range (e.g. `(-1.0, 1.0)`)?
- **How many bars of history does it need before it can produce a real
  signal** (a rolling window, a lookback period)? This becomes
  `min_bars_required`; before that many bars, the signal must be a
  well-defined placeholder (default `0.0`), not a guess or a crash.
- Whether they want more than one variant/parameter setting the way MAC
  has five speeds (e.g. an RSI strategy at both a 14-day and a 28-day
  lookback).
- **How rigorously they want the "is the formula actually right" check
  done** -- this is a real trade-off, not a formality, so offer it as an
  actual choice rather than deciding it for them:
    1. **A golden example** (most rigorous): a tiny, hand-computed test
       case. Catches a subtly wrong formula -- a sign error, the wrong
       window -- that nothing else here can. Costs the person a few
       minutes of arithmetic (or costs you, the LLM, doing it carefully
       and showing your work, which they should sanity-check).
    2. **A trend-sanity check** (the default if they don't have a
       preference): fully automatic, no manual arithmetic from anyone --
       generates a synthetic pure uptrend and downtrend and confirms the
       strategy agrees with the obvious direction on each. Real, but
       weaker: catches backwards comparison logic, not a subtly wrong
       formula that still happens to point the right direction.
    3. **Neither**: rely on the five checks in Step 4 that always run,
       plus your own read of whether the code looks right. Cheapest,
       weakest on this one dimension -- fine for a low-stakes exploration,
       worth saying so plainly if that's what's being chosen.

A plausible default beats stalling on details -- this is meant to be a
draft-and-approve conversation, the same as everywhere else in this
project, not a spec that has to be perfect on the first try.

## Step 3: Draft VARIANTS + compute_variant_signal + role file (+ a golden example, if that's what was chosen)

Follow the shape of the three examples exactly:

- A `VARIANTS` dict: variant name -> whatever params the compute function
  needs.
- A compute function, `def _<name>_compute_variant_signal(bars, params) ->
  List[float]`. `bars` is one ticker's full list of daily bar dicts
  (date/open/high/low/close/volume). Return one signal value per bar,
  where `signal[t]` may only depend on `bars[0..t]` -- step 4 checks this,
  it isn't just a promise.
- A role file `roles/<name>_signal.py` that imports `make_signal_computer`
  from `_signal_common` and registers an `AgentRoleEntry`, exactly like the
  three existing files -- copy one and adapt it rather than writing this
  part from scratch.
- **If a golden example was chosen in Step 2**: 5-10 bars, hand-computed
  (not generated by running the function itself), with the expected
  signal worked out by hand. Pick parameter values that make the
  arithmetic easy -- e.g. an EWMA span where `alpha = 2/(span+1)` comes
  out to a round number like 1.0 or 0.5 -- not the strategy's real
  production variants; the point is to make the arithmetic checkable by
  a human, not to test a realistic case. Show the arithmetic, don't just
  assert the answer, so the person can actually sanity-check it.
- **If a trend-sanity check was chosen instead**: nothing extra to draft
  here -- it's generated automatically in Step 4 from `signal_type` alone.

## Step 4: Run the strategy-contract checker before wiring anything in

Use the bundled `scripts/check_no_lookahead.py` against the new compute
function, on real data (e.g. the connected repo's `sp100_data/` CSVs),
before touching `office.md`. Five checks always run; the sixth is
whichever of golden-example / trend-sanity / neither was chosen in Step 2:

```python
from check_no_lookahead import assert_strategy_contract

assert_strategy_contract(
    my_compute_fn, my_params, real_bars,
    signal_type="directional",       # or "sizing"
    signal_range=None,               # e.g. (-1.0, 1.0) if signal_type="sizing"
    min_bars_required=20,            # or None if there's no warm-up period

    # pick ONE of these two (or leave both unset if "neither" was chosen):
    golden_bars=my_golden_bars, golden_expected=my_golden_signal,
    # trend_sanity=True,
)
```

Always run, regardless of Step 2's choice -- cheap enough that there's
no real reason to ever skip them:

1. **No lookahead** (the original, most important check): recomputes the
   signal on a history truncated right after day t and confirms day t's
   value doesn't change. A strategy that accidentally uses tomorrow's
   price will backtest as implausibly good, and nobody notices until it
   matters.
2. **Deterministic**: calling the function twice on identical inputs must
   return identical output -- catches hidden randomness, wall-clock
   reads, or accidental shared mutable state.
3. **Finite values only**: no NaN or infinity anywhere in the signal --
   catches a division-by-zero-style bug (an unfilled lookback window, an
   average-loss of zero) that no-lookahead can't see.
4. **Declared range, enforced** (if `signal_type` given): every value
   actually satisfies what was declared in Step 2.
5. **Warm-up period, enforced** (if `min_bars_required` given): every day
   before that count is the declared placeholder, not garbage.

The one optional dimension, per Step 2's choice:

6a. **Matches the golden example** (`golden_bars`/`golden_expected`): the
    most rigorous option -- catches a strategy that's confidently
    computing the wrong thing.
6b. **Trend sanity** (`trend_sanity=True`): generates a synthetic pure
    uptrend and downtrend automatically (no bars to hand-craft) and
    confirms the strategy agrees with the obvious direction on each.
    Weaker than 6a -- a strategy off by a constant factor or using the
    wrong window can still pass this -- but real, and free.
6c. **Neither**: only checks 1-5 run. Say so plainly when reporting
    results, rather than letting it look like the same level of
    verification as 6a or 6b.

If this raises, fix the compute function before proceeding. Do not wire a
strategy into the office that hasn't passed this check.

## Step 5: Wire it into office.md

Add, following the pattern already there for MAC/Donchian/Turtle:

- One new SIGNAL_COMPUTER agent for the strategy (using the new role).
- One `backtester(speed_name='<variant_name>')` agent per variant -- reuse
  the existing shared `backtester` role, don't create new backtester
  files, there should only ever be one.
- Extend JOIN's (`synchronizer`) inports list to include the new variant
  name(s).
- Wire the new SIGNAL_COMPUTER into the shared source, and each new
  backtester's output into JOIN, exactly like the three existing
  strategies.

EVALUATOR needs no changes -- it already handles however many variants
JOIN hands it.

## Step 6: Run it and verify

Verify by actually running `dsl build`/`dsl run` from a terminal against
real data -- that's the real path the user will run this through later, so
it's the one that has to actually work, not just something functionally
equivalent. (`compile_office` + `run_network` from Python is fine as a
quick first look while drafting, but don't let it stand in as the final
verification -- it can succeed in ways that `dsl run` doesn't, e.g. by
sidestepping how the generated runner resolves file paths.) Confirm: it
runs without crashing, and the new variant shows up correctly in
EVALUATOR's per-stock table and portfolio ranking. (Whether the signal
values themselves are in range is Step 4's job, not something to
re-eyeball here -- if Step 4 passed, trust it.)

If `dsl run` hits an error or produces suspicious output (e.g. every
strategy showing empty/zero results, not just the new one) that isn't
about the strategy you're adding, don't route around it so your own check
passes -- that leaves the office broken for whoever runs it next. Diagnose
it for real: is it pre-existing (check by testing the unmodified office,
e.g. via `git stash`), and can you fix the actual cause (a wrong path in
`office.md`, a stale generated `build/`, etc.)? If you can fix it, fix it
and say so plainly, separately from the new strategy's own changes. If you
genuinely can't (it's outside what you have access to, or outside this
task's scope), tell the user exactly what's broken and why, rather than
quietly working around it and reporting success. Offer to regenerate
`make_report.py`'s `report.html` so the user has something readable to
look at, not just console output.

## Showing the working: `explain_strategy.py`

When the user asks *"is this the strategy I meant?"*, *"show me the
steps"*, *"show me a few days"*, or wants to see why a signal is what
it is -- **run the script; do not describe the strategy from the
code.** A description is your reading of the role. The script's
numbers come from the role itself.

```bash
cd dissyslab/gallery/apps/mac_speed_suite
python3 explain_strategy.py --strategy donchian --variant 20 --ticker NVDA
```

It writes `strategy_working.xlsx`: one row per trading day, every
intermediate the strategy computed (the channel bounds, the two moving
averages), the same quantity again as a live Excel formula, a match
column, and a sentence naming the rule that fired.

Options, all repeatable or optional:

```
--strategy donchian --strategy mac    one sheet each
--variant 20 | 55 | fast | med | slow
--ticker NVDA        --bars 300:340        --rows 25
--out somewhere.xlsx
```

With no `--bars` it picks a window containing a signal change. With no
price CSV it falls back to a synthetic series and says so.

**Requires `openpyxl`** (`pip install "dissyslab[market]"`). If it is
missing, say so and offer to install it -- do not write the workbook
some other way.

**Then tell the user what to look at.** Point at one shaded formula
cell and read it back in words: `=MAX(C2:C21)` in row 22 means the
channel uses the twenty rows above this one and not this one. That
boundary convention is what the user is actually checking, and it is
invisible unless you name it.

**Be straight about what the two columns prove.** They are one
author's understanding of the rule written twice, so a misreading
appears in both. What the formula gives the user is a specification
they can read and change -- not a verification.

**Only Donchian and MAC have traces today.** Asked for Turtle or RS,
say so rather than improvising a trace: an explanation that does not
come from the role is the thing this script exists to avoid.

## Step 7: Confirm the diff stayed contained

Show a diff (`git diff` / `git status`) and confirm only new
strategy-specific files plus `office.md` changed -- `_backtester_core.py`,
`evaluator.py`, and `_signal_common.py` should show zero changes. This is
the actual point of the exercise: if a shared file needed editing,
something about the new strategy didn't fit the contract as designed,
which is worth telling the user directly rather than quietly patching
around it.

## Setting run parameters (basket, history window, validation, cost)

Users tune a run by talking, not by editing files. When the user
asks to change a parameter, make the edit for them, run it, and confirm by
pointing at the report's **"Run settings"** panel (top of `report.html`),
which records exactly what the run used -- so every result says which
parameters produced it. The knobs, and where each lives in `office.md`:

- **Basket (which stocks).** The `tickers=[...]` list on the `Sources:` line.
  After changing it, re-run the downloader
  (`python3 download_stock_history_from_yf.py`) so the CSVs match the new
  basket -- it reads the same list, so office and data can't drift -- then
  run. A requested ticker with no CSV yet is fetched by the downloader.
- **History window (how far back).** Set by which `*_10_year.csv` files exist
  and the `filename_pattern` on the `Sources:` line, i.e. how much history the
  downloader pulled. To change how much is downloaded, adjust the downloader's
  years argument and re-download.
- **Validation.** On the `GATE is a validation_gate(...)` line: `n_samples`
  (Monte Carlo resamples), `n_folds` (walk-forward folds), and
  `monte_carlo=False` / `walk_forward=False` to turn a half off. The default
  runs both in one pass.
- **Stop for R.** `stop_pct` on the same `GATE` line (default `0.10` = a 10%
  stop). R multiples in the report are each trade's return divided by this stop
  distance -- a disclosed assumption the user sets, never advice. Just change
  the number, e.g. `validation_gate(n_samples=100, stop_pct=0.05)`.
- **Transaction cost.** `cost_bps` (default 5). To change it, add
  `cost_bps=<value>` to every `backtester(...)` line and keep them identical --
  if they disagree, the report shows the cost as unknown, which is the signal
  that one was missed.

The report also shows **trade statistics** (count, average hold, win rate,
average win/loss, expectancy, reward:risk) and **R multiples** for every
variant, plus a per-variant list of the actual trades -- so when the user asks
"how many trades was that?" or "show me the twelve", the answer is already
in `report.html`; point them at it.

Always echo the change back in the user's own terms, and after the run confirm
the "Run settings" panel reflects it. Never silently apply a different value
than asked; if you had to interpret the request ("the last five years" -> a
date cutoff), say what you assumed -- the same disclosure discipline as Step 2.

## When this doesn't fit

Some strategies genuinely don't fit this contract, and it's better to say
so than to force it. Anything that needs to look across multiple tickers
at once to decide a single ticker's signal -- pairs trading, cross-
sectional ranking, sector rotation -- needs a different worker shape than
"one ticker's bars in, one signal series out." Flag this to the user
rather than bending `compute_variant_signal` to secretly take extra
tickers as a hidden argument.
