# Office: webhook_listener

Sources: webhook(port=8000, path="/webhook")
Sinks: console_printer,
       jsonl_recorder(path="webhook_log.jsonl")

Agents:
Alex is an analyst.

Connections:
webhook's destination is Alex.
Alex's keep is console_printer.
Alex's discard is jsonl_recorder.
