# Office: web_monitor

Sources: web(url="https://www.anthropic.com/news", poll_interval=300, max_items=3)
Sinks: console_printer,
       jsonl_recorder(path="web_monitor.jsonl")

Agents:
Alex is an analyst.

Connections:
web's destination is Alex.
Alex's summary is console_printer.
Alex's discard is jsonl_recorder.