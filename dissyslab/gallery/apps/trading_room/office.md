# Office: trading_room

# Validation fixture for the generic `select` coordinator
# (dissyslab.office.library.select_role), added to close task #31: does the
# generic implementation match OfficeSpeak's own worked example,
# start_gallery/trading_room.md, Case 2 (the "freeze while waiting for the
# ledger's reply" correction)? One trader only -- a second trader watching
# market data (as OfficeSpeak's own example has) would exercise the exact
# same select mechanism a second time, not new coverage, so it's omitted here
# to keep this fixture small and fast.
#
# What this validates: SelectNews must withhold every later news item while
# Trader is waiting for the ledger's reply to an earlier proposed trade, and
# must resume forwarding news only once Trader explicitly commands it to.

Sources: starter
Sinks: jsonl_recorder(path="trades.jsonl"), console_printer

Agents:
News       is a news_feed.
SelectNews is a select(inports=["info", "reply"], command="command").
Trader     is a trader_news.
Ledger     is a ledger.

Connections:
starter's destination is News.

News's out is SelectNews's info.
Ledger's reply_news is SelectNews's reply.

SelectNews's out is Trader.

Trader's request is Ledger.
Trader's command is SelectNews's command.
Trader's trade is jsonl_recorder, console_printer.
