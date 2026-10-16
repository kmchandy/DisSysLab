# mac_speed_suite: four families of trend-following rules, 11 variants,
# backtested on five stocks, validated walk-forward and by Monte Carlo.

sources:
    prices: csv_stock_history(tickers=["AMD", "NFLX", "NVDA", "PLTR", "TSLA"], filename_pattern="{ticker}_10_year.csv")

sinks:
    scorecard_report(path="report.html")

agents:
    Plan: plan(n_folds=4, n_samples=100, seed=42, block_size=20, stop_pct=0.10)
    MKT: market_context
    MAC: mac_signal
    DON: donchian_signal
    TURTLE: turtle_signal
    RS: rs_trend

    BT_MAC_FAST: backtester(variant="mac_fast")
    BT_MAC_MED_FAST: backtester(variant="mac_med_fast")
    BT_MAC_MED: backtester(variant="mac_med")
    BT_MAC_MED_SLOW: backtester(variant="mac_med_slow")
    BT_MAC_SLOW: backtester(variant="mac_slow")
    BT_DONCHIAN_20: backtester(variant="donchian_20")
    BT_DONCHIAN_55: backtester(variant="donchian_55")
    BT_TURTLE_S1: backtester(variant="turtle_s1")
    BT_TURTLE_S2: backtester(variant="turtle_s2")
    BT_RS_FAST: backtester(variant="rs_fast")
    BT_RS_SLOW: backtester(variant="rs_slow")

    JOIN: synchronizer(on="span", collect="results")
    EVAL: evaluate
    CMP: comparator
    Rex: router(on="msg_type")

connections:
    prices -> Plan -> MKT -> MAC, DON, TURTLE, RS
    MAC -> BT_MAC_FAST, BT_MAC_MED_FAST, BT_MAC_MED, BT_MAC_MED_SLOW, BT_MAC_SLOW
    DON -> BT_DONCHIAN_20, BT_DONCHIAN_55
    TURTLE -> BT_TURTLE_S1, BT_TURTLE_S2
    RS -> BT_RS_FAST, BT_RS_SLOW
    BT_MAC_FAST -> JOIN.mac_fast
    BT_MAC_MED_FAST -> JOIN.mac_med_fast
    BT_MAC_MED -> JOIN.mac_med
    BT_MAC_MED_SLOW -> JOIN.mac_med_slow
    BT_MAC_SLOW -> JOIN.mac_slow
    BT_DONCHIAN_20 -> JOIN.donchian_20
    BT_DONCHIAN_55 -> JOIN.donchian_55
    BT_TURTLE_S1 -> JOIN.turtle_s1
    BT_TURTLE_S2 -> JOIN.turtle_s2
    BT_RS_FAST -> JOIN.rs_fast
    BT_RS_SLOW -> JOIN.rs_slow
    JOIN -> EVAL -> CMP -> Rex
    Rex.next -> Plan
    Rex.scorecard -> scorecard_report
