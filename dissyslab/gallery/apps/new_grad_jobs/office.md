# Office: new_grad_jobs

# A sense → think → respond office contributed by Nyasha; see
# docs/PATTERN_sense_think_respond.md.

Sources: hacker_news(max_articles=10, poll_interval=600)
Sinks: intelligence_display, jsonl_recorder(path="jobs.jsonl")

Agents:
Jordan is a screener.
Casey is a formatter.

Connections:
hacker_news's destination is Jordan.

Jordan's formatter is Casey.
Jordan's discard is jsonl_recorder.

Casey's job_board are intelligence_display and jsonl_recorder.
