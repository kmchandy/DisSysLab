# Office: Job Hunter

Sources: hacker_news(max_articles=15, poll_interval=1800),
         python_jobs(max_articles=15, poll_interval=1800),
         remoteok(max_articles=15, poll_interval=1800),
         we_work_remotely(max_articles=15, poll_interval=1800)
Sinks: intelligence_display(max_items=10),
       jsonl_recorder(path="matched_jobs.jsonl"),
       gmail_sink(to="theroast08@gmail.com", subject="Job Match")

Agents:
Alex is a screener.
Morgan is a matcher.

Connections:
hacker_news's destination is Alex.
python_jobs's destination is Alex.
remoteok's destination is Alex.
we_work_remotely's destination is Alex.
Alex's relevant is Morgan.
Alex's discard is jsonl_recorder.
Morgan's matched_jobs are intelligence_display, jsonl_recorder, and gmail_sink.
