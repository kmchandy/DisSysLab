# mac_speed_suite — a trend-following backtester

Backtests a suite of trend-following strategies on a basket of stocks and writes
a ranked `report.html`. Included strategies: moving-average crossover (five
speeds), Donchian channels, the Turtle system, and a relative-strength trend
rule. Results are net of transaction costs and shown with a strategy-correlation
view, so you can see which "different" strategies are actually the same bet.


## Getting the price data

Nothing here ships market data — Yahoo's terms do not permit
redistributing it, so you download your own once:

```bash
pip install "dissyslab[market]"
dsl fetch-prices --office .
```

Files land in `~/.dissyslab/market_data` (or `$DSL_MARKET_DATA` if you
set it), which every office shares and which does not change when you
copy this office somewhere else with `dsl init`.

Better, ask your assistant: *"download the price history this office
needs."* That is the intended path — `dsl fetch-prices` exists so the
download is something you ask for rather than a terminal command you
have to know about.

(`download_stock_history_from_yf.py` still works and does the same
thing. It needs you to be standing in this folder.)


## New here? Try it by talking to Cowork

If you are not a programmer — or just want the guided path — you can drive the
whole thing in plain English through **Claude Cowork** instead of the command
line: describe a trading strategy in your own words and it gets added, run, and
validated for you. A step-by-step walk-through (get the repo, connect the folder,
install the `dsl` engine, install the skill, download the data, then run and read
the report) is in
[skill_for_testers/TEST_INSTRUCTIONS.md](skill_for_testers/TEST_INSTRUCTIONS.md).
The rest of this README is the command-line reference for those steps.

## Get the data (one time)

The price history is **not shipped with the repository** — it's vendor data from
Yahoo Finance, so each user downloads their own copy. From the repository root, change into
this office's folder and run:

```
cd dissyslab/gallery/apps/mac_speed_suite
pip install yfinance
python3 download_stock_history_from_yf.py
dsl run .
```

- `pip install yfinance` installs the downloader's one dependency.
- `python3 download_stock_history_from_yf.py` reads the ticker list, data
  directory, and filename pattern from `office.md`, then fetches each ticker's
  history — split/dividend adjusted — into `DisSysLab/sp100_data/` as
  `TICKER_10_year.csv`.
- `dsl run .` runs the office and writes `report.html` next to it.

If you skip the download, the office has no data to read and stops with a clear
error rather than silently reporting empty results.

To fetch a single ticker instead:

```
python3 download_stock_history_from_yf.py AAPL 10 AAPL_10_year.csv
```

## How the basket is specified

The stocks are specified in exactly one place: the `tickers=[...]` list in
`office.md`'s `Sources:` line. To change the basket — add, remove, or replace
tickers — edit that list, re-run the downloader (it reads the same list, so it
fetches exactly what the office uses), then `dsl run .`. The office and the
downloader read the one list, so they can't drift.

## Validation: walk-forward and Monte Carlo

By default the office runs **both** validations in a single pass -- no editing.
The `validation_gate` first runs **walk-forward out-of-sample validation**
(rank the variants on earlier windows, measure them on later windows they had
no part in choosing, so the report's headline is the out-of-sample ranking),
and then a **Monte Carlo robustness** pass (resample the history many times and
re-run, to see how much of the result is luck). The report shows both sections:
the out-of-sample scorecard and a per-variant outcome distribution (median
return, a 5th-95th band, worst-case drawdown, and probability of loss).

The Monte Carlo sample count is modest by default so the run stays quick.
Everything is adjustable on the gate line in `office.md` (or just by asking
Cowork in plain English):

    GATE is a validation_gate(n_samples=100).        # the default: both
    GATE is a validation_gate(n_samples=500).        # tighter distribution
    GATE is a validation_gate(monte_carlo=False).    # walk-forward only (fast)
    GATE is a validation_gate(walk_forward=False).   # Monte Carlo only

More samples give a smoother distribution but take longer. The point of the
design is that both validations drive the *same* in-office loop -- time slices
for walk-forward, a resampled bank for Monte Carlo -- so the pipeline, the
comparator, and the report are identical either way. (`window_gate` and
`monte_carlo_gate` remain available if you want a single-purpose run.)

## Trade statistics and R multiples

Beyond the return-series metrics (Sharpe, annualized return, drawdown), the
report shows the properties of **trades** -- for each variant: number of trades,
average hold, win rate, average win vs average loss, expectancy, and
reward:risk -- plus a collapsible list of the actual trades. Two rules with the
same Sharpe can trade completely differently, and a variant that never took a
position now reads as an explicit **0 trades**, not a flat 0%.

Results are also shown in **R multiples**: each trade's return divided by a
disclosed stop distance (`stop_pct` on the `GATE` line, default a 10% stop), so
outcomes read in the risk units traders use ("+2.1R"). R is shown *alongside*
the other numbers, never as an imposed position-sizing methodology -- the stop
is an assumption you set, not advice. Change it on the gate line, e.g.
`validation_gate(stop_pct=0.05)`.

The walk-forward section also stages the honest comparison directly: if you had
picked the in-sample winner, where did it actually rank out-of-sample, and which
variants are strong in *both* halves.

Every run stamps a **Run settings** panel at the top of the report recording the
exact basket, window, validation, stop, and cost that produced it. For the
plain-English way to drive all of this through Cowork, see
[skill_for_testers/COWORK_EXAMPLES.md](skill_for_testers/COWORK_EXAMPLES.md).

## Seeing the working — `explain_strategy.py`

`report.html` answers *how did it do*. This answers a different
question: **is this the strategy I meant?**

```bash
python3 explain_strategy.py --strategy donchian --variant 20 --ticker NVDA
python3 explain_strategy.py --strategy donchian --strategy mac --rows 25
python3 explain_strategy.py --strategy mac --variant med --bars 300:340
```

It writes `strategy_working.xlsx`: one row per trading day, and every
quantity the strategy computed on the way to its decision — the channel
bounds for Donchian, the two moving averages for MAC — with a plain
sentence saying which rule fired.

Each derived quantity appears **twice**: the value the Python produced,
and the same quantity as a live Excel formula over the price cells,
with a `match` column comparing them. The formula is there to be read.
`=MAX(C2:C21)` in row 22 says *"the twenty rows above this one, not
this one"* without anyone explaining the boundary convention. Change a
price and those shaded columns recompute.

### The signal column does not move

It is a number Python worked out and wrote into the cell, not a
formula, so nothing recalculates it when you change a price. A tester
changed a close to 99 against a channel top of 1.55 and the sheet said
*"no breakout -- hold"* — a confident wrong answer to the exact
question the sheet invites. This README used to promise otherwise.

For **Donchian** and the **moving-average crossover** the position is a
function of that row alone, so a live signal column is possible. Add
one and paste in the formula, filling down from row 3:

```
Donchian   =IF(F3="",0,IF(E3>F3,1,IF(E3<I3,-1,N2)))
MA cross   =IF(D3>G3,1,-1)
```

Seed Donchian's first row with the value from the `signal` column, then
fill down. `N2` points at the row above, which is how *"hold whatever
you held"* survives being written as a formula; the `F3=""` guard is
for the warm-up rows, where the channel does not exist yet and Excel
would otherwise read a blank cell as zero. Column letters assume the
default layout — check the header row if you passed `--strategy` more
than once.

Verified against the Python by recalculating both sheets: 43 rows for
Donchian, 30 for MAC, no disagreement. The Donchian formula is Sebu's,
with the blank guard added.

For **Turtle** and **relative strength** no such formula exists, and
this is the interesting half. Turtle's position depends on the whole
path — how many units are on, where the last one was added, where the
stop is — so no cell can compute it from one row. Relative strength
depends on the *other stocks in the basket*, which are not on this
sheet at all. Those two sheets show the position as a number with the
rule that fired beside it, and that is the honest presentation rather
than a limitation to be worked around.

The two columns do not verify each other; both express one author's
understanding of the rule. What they give you is a specification you
can read, in a language you already trust.

**Defaults worth knowing.** With no `--bars`, a window is chosen that
contains a signal change — twenty bars in which nothing happens
demonstrate nothing. Rows the formulas need but you did not ask for are
included and shaded grey, so a 20-day Donchian window carries twenty
rows of context. MAC cannot be recomputed from a window at all, since
an exponential average depends on every earlier bar, so its first
visible row is seeded from the full run and the recurrence proceeds
from there. With no price CSVs on disk it uses a synthetic series and
says so, in capitals, on the Read me sheet.

**It cannot silently disagree with the strategy it explains.** The
intermediates are recomputed and then checked against the signal the
real role produced. In both strategies the signal is a function of the
intermediates alone, so agreement on one is agreement on the other. On
a mismatch it names the bar and writes nothing.

Formula cells have no cached value until a spreadsheet application
opens the file, so `pandas.read_excel` sees blanks where Excel sees
numbers.

## Add a strategy

Add one role file under `roles/` (a per-day compute function plus a small
variants table) and a few lines in `office.md`; the shared machinery — the
backtester, evaluator, and report — needs no changes. See `PHASE1_DESIGN.md` for
the reuse contract and worked examples, and `roles/rs_trend.py` for a strategy
that uses cross-sectional (relative-strength) context supplied by the
`market_context` stage.
