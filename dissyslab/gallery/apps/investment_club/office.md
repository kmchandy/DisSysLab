# Office: investment_club

# Validation fixture for the generic `record` + `gate` roles
# (dissyslab.office.library.record_role / gate_role), added to close task
# #32: does the generic implementation match OfficeSpeak's own worked
# example, start_gallery/investment_club.md, Case 2 (the "famous
# correction" -- the accountant must read current holdings before pricing
# a trade, not just the proposed move)?
#
# What this validates: the accountant's fee for period N+1 must reflect
# exactly what the manager wrote to the ledger in period N -- proving (a)
# record's read/write protocol works, and (b) gate correctly keeps periods
# from overlapping, so no period's accountant ever sees a half-written or
# stale ledger.

Sources: starter
Sinks: jsonl_recorder(path="periods.jsonl"), console_printer

Agents:
Feed       is a period_feed.
Gate       is a gate.
Val        is a val_analyst.
Oppo       is a oppo_analyst.
Join       is a synchronizer(inports=["val", "oppo"]).
Manager    is a manager.
Accountant is a accountant.
Ledger     is a record(initial={"aapl_shares": 0, "cash": 10000.0}).

Connections:
starter's destination is Feed.

Feed's out is Gate's data.
Gate's out is Val, Oppo.

Val's out is Join's val.
Oppo's out is Join's oppo.

Join's out is Manager.

Manager's to_accountant is Accountant.
Accountant's to_ledger is Ledger.
Ledger's out is Accountant.
Accountant's to_manager is Manager.

Manager's to_ledger is Ledger.
Manager's out is jsonl_recorder, console_printer.
Manager's done is Gate's control.
