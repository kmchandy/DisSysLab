# Office: job_hunter

Sources: hacker_news(max_articles=15, poll_interval=1800),
         python_jobs(max_articles=15, poll_interval=1800),
         remoteok(max_articles=15, poll_interval=1800),
         we_work_remotely(max_articles=15, poll_interval=1800)
Sinks: intelligence_display(max_items=10),
       jsonl_recorder(path="matched_jobs.jsonl"),
       jsonl_recorder_discard(path="discarded_jobs.jsonl"),
       job_html_sink(path="matched_jobs.html", max_items=50),
       gmail_sink_match(to="you@example.com", subject="Job Match"),
       gmail_sink_tailor(to="you@example.com", subject="Tailored Resume"),
       gmail_sink_cover_letter(to="you@example.com", subject="Cover Letter Draft"),
       gmail_sink_research(to="you@example.com", subject="Company Brief")

Agents:
Alex is a screener.
Morgan is a matcher.
Riley is a tailor.
Dakota is a drafter.
Sage is a researcher.

Connections:
hacker_news's destination is Alex.
python_jobs's destination is Alex.
remoteok's destination is Alex.
we_work_remotely's destination is Alex.
Alex's relevant is Morgan.
Alex's discard is jsonl_recorder_discard.
Morgan's matched_jobs are intelligence_display, jsonl_recorder, job_html_sink, gmail_sink_match, Riley, Dakota, and Sage.
Riley's tailored is gmail_sink_tailor.
Dakota's cover_letters is gmail_sink_cover_letter.
Sage's research_briefs is gmail_sink_research.
