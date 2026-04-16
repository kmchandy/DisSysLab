# Office: calendar_briefing

Sources: calendar(poll_interval=300, days_ahead=7)
Sinks: console_printer,
       jsonl_recorder(path="calendar_briefing.jsonl")

Agents:
Alex is an analyst.

Connections:
calendar's destination is Alex.
Alex's briefing is console_printer.
