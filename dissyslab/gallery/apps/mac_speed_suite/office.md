# Office: mac_speed_suite

# The tester's original ask (paper/transcript_sp100_trend_following.md):
# several traditional trend-following rules (Man/AQR/Mulvaney-style moving-
# average crossover, the Turtle system, Donchian channels), backtested and
# ranked on SP100 stocks with return/volatility/Sharpe/Calmar/etc.
#
# Three strategy families, each with its own SIGNAL_COMPUTER (one role file
# per family, see roles/) and its own set of BACKTESTER instances (one per
# variant -- BACKTESTER and EVALUATOR are shared, strategy-agnostic
# machinery; see roles/_signal_common.py and roles/_backtester_core.py for
# the reuse contract this depends on). Source data: 5 real SP100 tickers
# from local CSV files (DisSysLab/sp100_data). `dsl run`'s generated
# build/run.py chdirs into this office's own directory before running
# (the framework convention -- see that file's __main__ block -- so that
# relative paths like an audio_clip's "./samples/..." resolve next to the
# office regardless of where `dsl run` was invoked from). That means this
# `directory` argument must be relative to *this office folder*, not the
# repo root, hence the four "../" below to climb back up to DisSysLab/.

# ── RUN SETTINGS (the knobs testers tune, usually just by asking Cowork) ──
#   Basket ............ the tickers=[...] list on the Sources line below
#   History window .... which *_10_year.csv files exist (re-run the downloader
#                       after changing the basket); filename_pattern below
#   Validation ........ n_samples / n_folds / walk_forward / monte_carlo on the
#                       GATE line (validation_gate)
#   Transaction cost .. cost_bps (defaults to 5; pass cost_bps=... to backtester)
#   Stop for R ........ stop_pct on the GATE line (default 0.10 = a 10% stop);
#                       R multiple of a trade = its return / stop_pct
# Whatever a run actually used is echoed back in report.html's "Run settings"
# panel, so every report says exactly which parameters produced it.
Sources: csv_stock_history(tickers=['AMD', 'NFLX', 'NVDA', 'PLTR', 'TSLA'], directory='../../../../sp100_data', filename_pattern='{ticker}_10_year.csv')
Sinks: console_printer, report_html(path="report.html")

Agents:
# GATE runs BOTH validations in one pass: walk-forward (out-of-sample folds)
# followed by a Monte Carlo robustness distribution. The report shows both
# sections; no editing needed. The Monte Carlo sample count is modest by
# default so the run stays quick -- raise it for a tighter distribution, or
# turn either half off:
#   GATE is a validation_gate(n_samples=500).      # tighter Monte Carlo
#   GATE is a validation_gate(monte_carlo=False).  # walk-forward only (fast)
#   GATE is a validation_gate(walk_forward=False). # Monte Carlo only
#   GATE is a validation_gate(stop_pct=0.05).      # tighter stop for R multiples
GATE is a validation_gate(n_samples=100, stop_pct=0.10).
MKT is a market_context.
MAC_SIGNAL is a mac_signal.
DONCHIAN_SIGNAL is a donchian_signal.
TURTLE_SIGNAL is a turtle_signal.
RS_SIGNAL is a rs_trend.

BT_MAC_FAST is a backtester(speed_name='mac_fast').
BT_MAC_MED_FAST is a backtester(speed_name='mac_med_fast').
BT_MAC_MED is a backtester(speed_name='mac_med').
BT_MAC_MED_SLOW is a backtester(speed_name='mac_med_slow').
BT_MAC_SLOW is a backtester(speed_name='mac_slow').
BT_DON_20 is a backtester(speed_name='donchian_20').
BT_DON_55 is a backtester(speed_name='donchian_55').
BT_TURTLE_S1 is a backtester(speed_name='turtle_s1').
BT_TURTLE_S2 is a backtester(speed_name='turtle_s2').
BT_RS_FAST is a backtester(speed_name='rs_fast').
BT_RS_SLOW is a backtester(speed_name='rs_slow').

JOIN is a synchronizer(inboxes=['mac_fast', 'mac_med_fast', 'mac_med', 'mac_med_slow', 'mac_slow', 'donchian_20', 'donchian_55', 'turtle_s1', 'turtle_s2', 'rs_fast', 'rs_slow']).
EVAL is a evaluator.
CMP is a comparator.

Connections:
csv_stock_history's out is GATE.

GATE's out is MKT.

MKT's out are MAC_SIGNAL, DONCHIAN_SIGNAL, TURTLE_SIGNAL and RS_SIGNAL.

MAC_SIGNAL's out are BT_MAC_FAST, BT_MAC_MED_FAST, BT_MAC_MED, BT_MAC_MED_SLOW and BT_MAC_SLOW.
DONCHIAN_SIGNAL's out are BT_DON_20 and BT_DON_55.
TURTLE_SIGNAL's out are BT_TURTLE_S1 and BT_TURTLE_S2.
RS_SIGNAL's out are BT_RS_FAST and BT_RS_SLOW.

BT_MAC_FAST's out is JOIN's mac_fast.
BT_MAC_MED_FAST's out is JOIN's mac_med_fast.
BT_MAC_MED's out is JOIN's mac_med.
BT_MAC_MED_SLOW's out is JOIN's mac_med_slow.
BT_MAC_SLOW's out is JOIN's mac_slow.
BT_DON_20's out is JOIN's donchian_20.
BT_DON_55's out is JOIN's donchian_55.
BT_TURTLE_S1's out is JOIN's turtle_s1.
BT_TURTLE_S2's out is JOIN's turtle_s2.
BT_RS_FAST's out is JOIN's rs_fast.
BT_RS_SLOW's out is JOIN's rs_slow.

JOIN's out is EVAL.
EVAL's out is CMP.

CMP's next is GATE.
CMP's out are console_printer and report_html.
