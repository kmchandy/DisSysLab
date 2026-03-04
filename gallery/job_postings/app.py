# ============================================================
# Job Postings Monitor
# Monitors three remote job boards for relevant postings.
#
# Topology:
#   python_jobs ───┐
#   remoteok       ┼→ job_filter → ┬→ display
#   we_work_remotely┘              └→ batcher → report
#                       clock ─────┘
#
# Usage:
#   export ANTHROPIC_API_KEY='your-key'
#   python -m gallery.job_postings.app
# ============================================================

import json
from dsl import network
from dsl.blocks import Source, Transform, Sink
from components.sources.rss_normalizer import (
    python_jobs, remoteok, we_work_remotely,
)
from components.transformers.ai_agent import ai_agent
from components.transformers.stateful_agent import StatefulAgent
from components.sources.clock_source import ClockSource

# ── Configure Your Job Search ─────────────────────────────────
JOB_CRITERIA = """
I am a Python developer with 2 years of experience looking for a
remote backend or data engineering role. I am interested in companies
working on AI, climate tech, or developer tools.
"""

# ── Sources ───────────────────────────────────────────────────
py_feed = python_jobs(max_articles=20,      poll_interval=3600)
rok_feed = remoteok(max_articles=20,         poll_interval=3600)
wwr_feed = we_work_remotely(max_articles=20, poll_interval=3600)

py_source = Source(fn=py_feed.run,  name="python_jobs")
rok_source = Source(fn=rok_feed.run, name="remoteok")
wwr_source = Source(fn=wwr_feed.run, name="we_work_remotely")

# ── AI Agents ─────────────────────────────────────────────────
relevance_agent = ai_agent(f"""
Given this job seeker profile:
{JOB_CRITERIA}

Does this job posting look like a good match?
Return JSON only, no explanation: {{"relevant": true or false, "reason": "one sentence"}}
""")

reporter_agent = ai_agent(f"""
You receive a JSON batch of job postings grouped by source in by_source.
The job seeker is looking for: {JOB_CRITERIA}

Write a concise daily job digest. Group postings by source.
For each posting include the title and why it matches the candidate's profile.
Highlight the top 3 most promising postings at the top.
Return plain text, not JSON.
""")

# ── Transform Functions ───────────────────────────────────────


def filter_jobs(article):
    if not article.get("text", "").strip():
        return None
    raw = relevance_agent(article["text"])
    if not raw.strip():
        return None
    result = json.loads(raw)
    if not result["relevant"]:
        return None
    article["reason"] = result["reason"]
    return article


def display(article):
    print(f"💼 [{article['source']:>16}] {article['title']}")
    print(f"   {article['reason']}")
    print(f"   {article['url']}")
    print()


def write_report(batch):
    return {"report": reporter_agent(json.dumps(batch, indent=2))}


def print_report(msg):
    print("\n" + "=" * 70)
    print("DAILY JOB DIGEST")
    print("=" * 70)
    print(msg["report"])
    print("=" * 70 + "\n")


# ── Batch Reporting ───────────────────────────────────────────
batcher = StatefulAgent(max_articles=200, clear_on_tick=True)
clock = ClockSource.daily()

# ── Build Nodes ───────────────────────────────────────────────
job_filter = Transform(fn=filter_jobs,  name="job_filter")
display_sink = Sink(fn=display,           name="display")
batcher_node = Transform(fn=batcher.run,  name="batcher")
clock_source = Source(fn=clock.run,       name="clock")
report_node = Transform(fn=write_report, name="report_writer")
report_sink = Sink(fn=print_report,      name="report_sink")

# ── Network ───────────────────────────────────────────────────
g = network([
    (py_source,  job_filter),
    (rok_source, job_filter),
    (wwr_source, job_filter),

    (job_filter, display_sink),
    (job_filter, batcher_node),

    (clock_source, batcher_node),
    (batcher_node, report_node),
    (report_node,  report_sink),
])

if __name__ == "__main__":
    print("\n💼 Job Postings Monitor")
    print("   Sources: Python.org, RemoteOK, We Work Remotely")
    print("   Streaming matches to console. Daily digest at midnight. Ctrl+C to stop.\n")
    g.run_network(timeout=None)
