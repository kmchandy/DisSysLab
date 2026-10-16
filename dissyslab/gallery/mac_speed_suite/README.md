# mac_speed_suite

Four families of trend-following rules -- moving-average crossover (5
speeds), Donchian channels (2), the Turtle system (2) and relative
strength (2) -- backtested on five stocks and ranked on return,
volatility, Sharpe, Calmar and more. Each run is validated twice:
walk-forward (a full span, then train/test folds) and Monte Carlo
(resampled histories).

    prices -> Plan -> MKT -> MAC, DON, TURTLE, RS
    MAC -> BT_MAC_FAST, ...            (one backtester per variant)
    BT_MAC_FAST -> JOIN.mac_fast  ...   (11 inboxes)
    JOIN -> EVAL -> CMP -> Rex
    Rex.next -> Plan                    (the loop: one span at a time)
    Rex.scorecard -> scorecard_report

- **Plan** sends one span at a time; **CMP** answers "next" until every
  span is done, then sends the scorecard. One span in the loop at a time
  keeps memory bounded (10 years of prices is not copied 109 times).
- **JOIN** is a synchronizer in its collected form: 11 identical
  backtesters, so their results are collected under `results`, not
  merged; each says which variant it is.
- **The run settings** are the arguments on two lines: `prices` (the
  basket) and `Plan` (folds, samples, stop), plus `cost_bps=` on the
  backtesters.
- **Adding a strategy:** a `roles/<name>_signal.py` with its variants and
  compute function, one backtester line per variant, one fan-out line and
  one `-> JOIN.<variant>` line per variant. The shared machinery
  (`roles/_*.py`) does not change.

Price files: `dsl fetch-prices` (see `docs/SOURCES_AND_SINKS.md`).
