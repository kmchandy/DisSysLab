# Office: stocks_monitor

Sources: stocks(ticker="AAPL", poll_interval=300)
Sinks: console_printer,
       jsonl_recorder(path="stocks_monitor.jsonl")

Agents:
Alex is an analyst.

Connections:
stocks's destination is Alex.
Alex's briefing is console_printer.