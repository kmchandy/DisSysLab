# Office: my_first_office

Sources: hacker_news(max_articles=10, poll_interval=600)
Sinks: console_printer,
       jsonl_recorder(path="my_first_office.jsonl")

Agents:
Alex is an analyst.
Morgan is an editor.

Connections:
hacker_news's destination is Alex.
Alex's editor is Morgan.
Alex's discard is jsonl_recorder.
Morgan's briefing are console_printer and jsonl_recorder.