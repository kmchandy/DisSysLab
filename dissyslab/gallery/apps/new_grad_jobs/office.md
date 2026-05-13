# Office: new_grad_jobs

# A sense → think → respond office that watches a tech-jobs feed
# and pulls out postings relevant to entry-level / new-grad / intern
# applicants in SWE, AI/ML, or Data Science. Each kept posting is
# rewritten as a clean scannable brief. Originally contributed by
# Nyasha; see docs/PATTERN_sense_think_respond.md for the family.


# ──────────────────────────────────────────────────────────────────
# SLOT 1: SOURCES  (sense)
# Where the office watches for new postings. Hacker News' "Who's
# Hiring" thread is the default. Swap in `python_jobs`, `techcrunch`,
# or a custom RSS source to focus on a different stream.
# ──────────────────────────────────────────────────────────────────
Sources: hacker_news(max_articles=10, poll_interval=600)


# ──────────────────────────────────────────────────────────────────
# SLOT 4: SINKS  (respond)
# Kept jobs render to the terminal AND a JSONL archive; the JSONL
# also catches the rejects so you can audit later what the screener
# dropped. Swap intelligence_display for markdown_digest, slack_sink,
# or any other sink to send the job board elsewhere.
# ──────────────────────────────────────────────────────────────────
Sinks: intelligence_display, jsonl_recorder(path="jobs.jsonl")


Agents:
# ──────────────────────────────────────────────────────────────────
# SLOT 2: THINKER  (screener)
# Decides whether each posting is relevant. Edit roles/screener.md
# to change the criteria (different role types, different seniority,
# different geography, different tech stack).
# ──────────────────────────────────────────────────────────────────
Jordan is a screener.

# ──────────────────────────────────────────────────────────────────
# SLOT 3: WRITER  (formatter)
# Reformats each kept posting into the structured brief Pat actually
# wants to read. Edit roles/formatter.md to change the output shape
# (add salary parsing, drop the "flags" field, change the summary
# length).
# ──────────────────────────────────────────────────────────────────
Casey is a formatter.


Connections:
hacker_news's destination is Jordan.

# Jordan's screener decision routes the posting to Casey (kept) or
# drops it into the JSONL audit log (rejected).
Jordan's formatter is Casey.
Jordan's discard is jsonl_recorder.

# Casey publishes each formatted brief to both the terminal and the
# JSONL archive.
Casey's job_board are intelligence_display and jsonl_recorder.
