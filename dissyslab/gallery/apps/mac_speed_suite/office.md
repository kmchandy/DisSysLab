# Office: mac_speed_suite

# Vikram's original ask (OfficeSpeak/paper/transcript_sp100_trend_following.md):
# several traditional trend-following rules (Man/AQR/Mulvaney-style moving-
# average crossover, the Turtle system, Donchian channels), backtested and
# ranked on SP100 stocks with return/volatility/Sharpe/Calmar/etc.
#
# Three strategy families, each with its own SIGNAL_COMPUTER (one role file
# per family, see roles/) and its own set of BACKTESTER instances (one per
# variant -- BACKTESTER and EVALUATOR are shared, strategy-agnostic
# machinery; see roles/_signal_common.py and roles/_backtester_core.py for
# the reuse contract this depends on). Source data: 5 real SP100 tickers
# from local CSV files (DisSysLab/sp100_data) -- run `dsl run` from the
# DisSysLab repo root so this relative `directory` resolves correctly.

Sources: csv_stock_history(tickers=['AMD', 'NFLX', 'NVDA', 'PLTR', 'TSLA'], directory='sp100_data')
Sinks: console_printer

Agents:
MAC_SIGNAL is a mac_signal.
DONCHIAN_SIGNAL is a donchian_signal.
TURTLE_SIGNAL is a turtle_signal.

BT_MAC_FAST is a backtester(speed_name='mac_fast').
BT_MAC_MED_FAST is a backtester(speed_name='mac_med_fast').
BT_MAC_MED is a backtester(speed_name='mac_med').
BT_MAC_MED_SLOW is a backtester(speed_name='mac_med_slow').
BT_MAC_SLOW is a backtester(speed_name='mac_slow').
BT_DON_20 is a backtester(speed_name='donchian_20').
BT_DON_55 is a backtester(speed_name='donchian_55').
BT_TURTLE_S1 is a backtester(speed_name='turtle_s1').
BT_TURTLE_S2 is a backtester(speed_name='turtle_s2').

JOIN is a synchronizer(inports=['mac_fast', 'mac_med_fast', 'mac_med', 'mac_med_slow', 'mac_slow', 'donchian_20', 'donchian_55', 'turtle_s1', 'turtle_s2']).
EVAL is a evaluator.

Connections:
csv_stock_history's out are MAC_SIGNAL, DONCHIAN_SIGNAL and TURTLE_SIGNAL.

MAC_SIGNAL's out are BT_MAC_FAST, BT_MAC_MED_FAST, BT_MAC_MED, BT_MAC_MED_SLOW and BT_MAC_SLOW.
DONCHIAN_SIGNAL's out are BT_DON_20 and BT_DON_55.
TURTLE_SIGNAL's out are BT_TURTLE_S1 and BT_TURTLE_S2.

BT_MAC_FAST's out is JOIN's mac_fast.
BT_MAC_MED_FAST's out is JOIN's mac_med_fast.
BT_MAC_MED's out is JOIN's mac_med.
BT_MAC_MED_SLOW's out is JOIN's mac_med_slow.
BT_MAC_SLOW's out is JOIN's mac_slow.
BT_DON_20's out is JOIN's donchian_20.
BT_DON_55's out is JOIN's donchian_55.
BT_TURTLE_S1's out is JOIN's turtle_s1.
BT_TURTLE_S2's out is JOIN's turtle_s2.

JOIN's out is EVAL.
EVAL's out is console_printer.
