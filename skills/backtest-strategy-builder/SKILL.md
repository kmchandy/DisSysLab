---
name: backtest-strategy-builder
description: Add or backtest a trading strategy in DisSysLab's backtest office, following its signal/backtest/evaluate contract, and verify it before wiring it in. Use whenever someone wants to add, draft, prototype or backtest a trading rule -- momentum, mean-reversion, RSI, MACD, breakout, moving-average, Donchian, Turtle, pairs -- even if they never say "mac_speed_suite" or "signal computer". Triggers: "backtest a new strategy", "add a trading rule", "try a momentum strategy on these stocks", "can we test an RSI rule", "what if we added mean reversion". Also use for changing a run's parameters in plain English -- which stocks, how far back, Monte Carlo samples, walk-forward folds, transaction cost: "use these eight stocks", "run 500 Monte Carlo samples", "test the last five years", "set costs to 10 bps". Requires the dissyslab package with the market extra, and a backtest office folder -- one whose office.md declares agents with `backtester(...)`, made by `dsl init mac_speed_suite my_backtest`.
---

# Adding a strategy to mac_speed_suite

**Skill version: `2026-08-26.d28fe85`.** If anyone asks which version of this
skill is loaded, answer with that string, exactly. A skill update can
report success while the old version stays resident.

## First: which folder are you working in?

**Settle this before anything else, and say out loud which folder you
settled on.** A backtest office is one whose `office.md` declares agents
with `backtester(...)` (`BT_MAC_FAST: backtester(variant="mac_fast")`).
That is a property every copy keeps; a path is
true in one copy of the world and `dsl init` makes copies where it is
false.

- **The user named a folder** -- use it.
- **They did not** -- look for directories holding an `office.md` with
  a `backtester(` line. Search where the user is
  working and under their home directory, not the whole filesystem.
- **One match** -- use it, and say which: *"Working in `~/my_backtest`
  -- it has BT_DONCHIAN_20 and ten other backtesters."* One line, and it
  is what lets them catch you on the day you are wrong.
- **Several** -- ask. Two backtest folders is normal for someone
  comparing versions of their own work.
- **None** -- offer to make one: `dsl init mac_speed_suite my_backtest`,
  then `dsl fetch-prices --office my_backtest`.
- **A match only inside the installed package** (a path containing
  `site-packages`, or `dissyslab/gallery/`) -- **treat it as none.**
  The gallery ships inside the wheel, so this match exists on every
  machine and is the one place you must never write: `dsl init` copies
  from it, and `pip install -U` erases anything added to it. A user
  whose strategy went there will run their own office and not find it.

**Every path in this document is relative to the folder you settled
on.** Where it says `roles/_signal_common.py`, it means that folder's
`roles/_signal_common.py`.

---

The backtest office already runs four strategies -- MAC, Donchian,
Turtle and relative strength (RS) -- all sharing one backtester role and
one evaluator.
Adding a new strategy means writing one new, small piece (a
`compute_variant_signal` function) and letting the existing, already-tested
BACKTESTER/EVALUATOR machinery do everything else. You should not need to
edit `_backtester_core.py`, `_evaluation.py`, or `_signal_common.py` to add a
strategy -- if you find yourself wanting to, stop and reconsider (see "When
this doesn't fit," at the end); that usually means the new idea doesn't
actually match this contract.

To change a run's **parameters** (basket, history window, validation, cost) rather than add a strategy, skip to "Setting run parameters" near the end -- that path is a quick edit and a re-run, not the seven steps below.

## Step 1: Read the contract and the three existing examples

Before writing anything, read these files in the folder you settled on:

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
- A role file `roles/<name>_signal.py`: the front matter in its
  docstring, then `VARIANTS` and the compute function, then one class
  that wraps them with `make_signal_computer` and copies `span` through.
  Copy `roles/rs_trend.py` and change the names rather than writing this
  part from scratch; the class is four lines:

  ```python
  class RsiSignal:
      def __init__(self, checks="on"):
          self.compute = make_signal_computer("rsi", RSI_VARIANTS, _rsi_compute_variant_signal, checks=checks)

      def __call__(self, item):
          ((out, _port),) = self.compute(item)
          return [{**out, "span": item["span"]}]
  ```
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
function, on real data -- the CSVs `dsl fetch-prices` downloaded, which
`dsl doctor` reports the location of --
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

Following the pattern already there for the other four, with `rsi` and
two variants `rsi_14`, `rsi_28` as the example:

```
agents:
    ...
    RSI: rsi_signal
    BT_RSI_14: backtester(variant="rsi_14")
    BT_RSI_28: backtester(variant="rsi_28")

connections:
    prices -> Plan -> MKT -> MAC, DON, TURTLE, RS, RSI
    ...
    RSI -> BT_RSI_14, BT_RSI_28
    BT_RSI_14 -> JOIN.rsi_14
    BT_RSI_28 -> JOIN.rsi_28
```

- One signal agent for the strategy, fed from `MKT` like the others.
- One `backtester(variant="<variant>")` line per variant. Reuse the shared
  `backtester` role; there should only ever be one.
- One `-> JOIN.<variant>` line per variant. The synchronizer's inboxes are
  the names its connections use, so this is all JOIN needs.

`EVAL` needs no change: it handles however many variants JOIN collects.
Run `dsl check .` before `dsl run`: a misspelt variant or inbox is
reported by line.

## Step 6: Run it and verify

Verify by actually running `dsl check .` and `dsl run .` from a terminal,
in the folder you settled on, against real data -- that is the path the
user will run this through later, so it is the one that has to work.
Confirm: it runs to the end with exit status 0, and the new variants show
up in `report.html`'s per-stock table and portfolio ranking. (Whether the signal
values themselves are in range is Step 4's job, not something to
re-eyeball here -- if Step 4 passed, trust it.)

If `dsl run` hits an error or produces suspicious output (e.g. every
strategy showing empty/zero results, not just the new one) that isn't
about the strategy you're adding, don't route around it so your own check
passes -- that leaves the office broken for whoever runs it next. Diagnose
it for real: is it pre-existing (check by testing the unmodified office,
e.g. via `git stash`), and can you fix the actual cause (a wrong path in
`office.md`, a missing price file, etc.)? If you can fix it, fix it
and say so plainly, separately from the new strategy's own changes. If you
genuinely can't (it's outside what you have access to, or outside this
task's scope), tell the user exactly what's broken and why, rather than
quietly working around it and reporting success. Point the user at
`report.html`, which the run writes, so they have something readable to
look at, not just console output.

## Showing the working

When the user asks *"is this the strategy I meant?"* or *"show me a few
days"*: the version 1 office had a script, `explain_strategy.py`, that
wrote every intermediate value to a workbook. This office does not have
it yet. Say so, rather than describing the strategy from the code as if
that were the same thing: a description is your reading of the role, not
the role's own numbers. What you can do honestly is run the compute
function on a short window of real bars in Python and show its output
beside the bars, saying that is what you did.

## Step 7: Confirm the diff stayed contained

Show a diff (`git diff` / `git status`) and confirm only new
strategy-specific files plus `office.md` changed -- `_backtester_core.py`,
`_evaluation.py`, and `_signal_common.py` should show zero changes. This is
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

- **Basket (which stocks).** The `tickers=[...]` list on the `prices:`
  line under `sources:`. After changing it, run
  `dsl fetch-prices --office .` so the price files match the new basket --
  it reads the same list, so office and data cannot drift -- then run.
- **History window (how far back).** Set by how much history was fetched
  (`dsl fetch-prices --office . --years 5`) and the `filename_pattern` on
  the `prices:` line; `start=` and `end=` on that line cut it further.
- **Validation.** On the `Plan: plan(...)` line: `n_samples` (Monte Carlo
  resamples), `n_folds` (walk-forward folds), and `monte_carlo=False` /
  `walk_forward=False` to turn a half off. The default runs both in one
  pass.
- **Stop for R.** `stop_pct` on the same `Plan` line (default `0.10` = a
  10% stop). R multiples in the report are each trade's return divided by
  this stop distance -- a disclosed assumption the user sets, never
  advice.
- **Transaction cost.** `cost_bps` (default 5). To change it, add
  `cost_bps=<value>` to every `backtester(...)` line and keep them
  identical -- if they disagree, the report shows the cost as unknown,
  which is the signal that one was missed.

The report also shows **trade statistics** (count, average hold, win rate,
average win/loss, expectancy, reward:risk) and **R multiples** for every
variant, plus a per-variant list of the actual trades -- so when the user asks
"how many trades was that?" or "show me the twelve", the answer is already
in `report.html`; point them at it.

Always echo the change back in the user's own terms, and after the run confirm
the "Run settings" panel reflects it. Never silently apply a different value
than asked; if you had to interpret the request ("the last five years" -> a
date cutoff), say what you assumed -- the same disclosure discipline as Step 2.

## What a signal can and cannot say

**Read this before agreeing to build risk management.** The gap below is
invisible in the output: you will produce plausible code, the office will
run it, the report will rank it, and it will not be what was asked for.

`_backtester_core` computes `gross = prior_signal * today_return`, so a
signal is a **position fraction**, not a direction. `0.5` means half a
position and the backtest handles it correctly.

**Expressible**, being a property of one ticker's own history: position
size scaled by that ticker's own volatility; pyramiding in and out, as
Turtle does; a stop expressed as an exit to `0.0`; anything computable
from `bars[0..t]` for that one ticker.

**Not expressible at all**, because signals are computed per ticker with
no shared state: total risk across open positions; a cap on correlated
markets or units per sector; sizing against current account equity,
which depends on every other position's path; rebalancing between
tickers.

So when someone asks for *"Turtle-style risk management"*, half of what
they mean is available and half is not. Say which half, in those terms,
before writing anything:

> *I can size each position by that stock's own volatility and pyramid
> the way Turtle does — those are per-ticker rules. What I cannot do is
> cap total portfolio risk or limit correlated units, because each
> ticker's signal is computed without seeing the others. Do you want the
> per-ticker half, knowing that?*

**Do not** approximate a portfolio rule with a per-ticker one and give it
the portfolio rule's name. The backtest will look right.

## When this doesn't fit

Some strategies genuinely don't fit this contract, and it's better to say
so than to force it. Anything that needs to look across multiple tickers
at once to decide a single ticker's signal -- pairs trading, cross-
sectional ranking, sector rotation -- needs a different worker shape than
"one ticker's bars in, one signal series out." Flag this to the user
rather than bending `compute_variant_signal` to secretly take extra
tickers as a hidden argument.

## The three checks are no longer yours to remember

The office runs them itself. `make_signal_computer` verifies every
variant on its first real message -- no look-ahead, deterministic, every
value finite -- and raises `StrategyContractError` before anything is
ranked. You do not have to invoke them, and a strategy you forget to
check is checked anyway. About four seconds for nine variants over ten
years, once per run.

The fuller checks still need you, because they need declarations the
office does not carry: `signal_range`, `min_bars_required`, a golden
example, the trend-sanity pass. Run `assert_strategy_contract` with
those, as Step 4 describes.

If a check fires and the user is certain it is wrong, the waiver goes in
`office.md`, where anyone reading the office can see it:

```
DON: donchian_signal(checks="off")
```

Never a command-line flag. Six weeks later nobody can tell a run that
passed from a run that skipped.
