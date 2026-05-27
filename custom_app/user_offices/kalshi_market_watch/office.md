# Office: kalshi_market_watch

# Discovery mode: scans open Kalshi *events* and *markets*, streams one update
# per *event* (all outcome contracts + implied % and return-at-ask figures).
#
# Pick ONE style:
#   • keyword="gold" — matches event titles + market text containing gold
#   • series_ticker="KXWTI" — all open contracts in the WTI series (reliable for oil)
# Tuning: max_scan_events, max_scan_markets, poll_interval (first poll can be slow).
# Rate limits: page_delay_seconds / event_expand_delay_seconds space out HTTP calls;
# raise poll_interval (e.g. 180–300) if you still see 429s.

Sources: kalshi(keyword="gold", poll_interval=180, max_scan_events=8000, max_scan_markets=4000, page_delay_seconds=0.25, event_expand_delay_seconds=0.2)
Sinks: console_printer,
       jsonl_recorder(path="kalshi_market_watch.jsonl")

Agents:
Alex is an analyst.

Connections:
kalshi's destination is Alex.
Alex's briefing is console_printer.
