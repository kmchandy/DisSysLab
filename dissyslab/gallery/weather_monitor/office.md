# Office: weather_monitor

Sources: weather(city="Pasadena", poll_interval=3600)
Sinks: console_printer,
       jsonl_recorder(path="weather_monitor.jsonl")

Agents:
Alex is an analyst.

Connections:
weather's destination is Alex.
Alex's briefing is console_printer.