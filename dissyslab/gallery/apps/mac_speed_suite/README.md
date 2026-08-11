# mac_speed_suite — a trend-following backtester

Backtests a suite of trend-following strategies on a basket of stocks and writes
a ranked `report.html`. Included strategies: moving-average crossover (five
speeds), Donchian channels, the Turtle system, and a relative-strength trend
rule. Results are net of transaction costs and shown with a strategy-correlation
view, so you can see which "different" strategies are actually the same bet.

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

By default the office runs **walk-forward out-of-sample validation**: it ranks
the variants on earlier windows and measures them on later windows they had no
part in choosing, so the report's headline is the out-of-sample ranking. Change
the number of folds with `window_gate(n_folds=...)` in `office.md`.

To run a **Monte Carlo robustness** pass instead, swap the gate line in
`office.md`:

    GATE is a monte_carlo_gate(n_samples=200).

Everything else stays the same -- that is the point: the same in-office loop with
a resampled bank instead of time slices. The report then shows an outcome
distribution per variant (median return, a 5th-95th band, worst-case drawdown,
and probability of loss), so you can see how much of the result is luck. More
samples give a smoother distribution but take longer.

## Add a strategy

Add one role file under `roles/` (a per-day compute function plus a small
variants table) and a few lines in `office.md`; the shared machinery — the
backtester, evaluator, and report — needs no changes. See `PHASE1_DESIGN.md` for
the reuse contract and worked examples, and `roles/rs_trend.py` for a strategy
that uses cross-sectional (relative-strength) context supplied by the
`market_context` stage.
