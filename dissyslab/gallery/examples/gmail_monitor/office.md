# Office: gmail_monitor

Sources: gmail(poll_interval=60, max_emails=5, unread_only=True)
Sinks: console_printer,
       jsonl_recorder(path="gmail_monitor.jsonl")

Agents:
Alex is an analyst.

Connections:
gmail's destination is Alex.
Alex's summary is console_printer.
Alex's discard is jsonl_recorder.