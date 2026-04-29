Sources: hacker_news(max_articles=10, poll_interval=600)
Sinks: intelligence_display(max_items=8),
       jsonl_recorder(path="jobs.jsonl")

Agents:
Jordan is a screener.
Casey is a formatter.

Connections:
hacker_news's destination is Jordan.
Jordan's formatter is Casey.
Jordan's discard is jsonl_recorder.
Casey's job_board are intelligence_display and jsonl_recorder.