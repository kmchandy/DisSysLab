# examples/module_05/app.py

"""
Module 05: Job Postings Monitor — Demo Version

Monitors two demo job feeds, filters spam, checks relevance using a
demo AI agent, and routes matching postings to archive + display.

Network topology:
    python_jobs ─┐
                  ├→ spam_filter → relevance → split → out_0 → archive
    ml_jobs     ─┘                                  → out_0 → display
                                                    → out_1 → (discard)

No API keys needed. Uses demo job data and demo AI components.
To connect real RSS feeds and Claude AI, see app_live.py.

Run from the DisSysLab root directory:
    python3 -m examples.module_05.app
"""

import re
from dsl import network
from dsl.blocks import Source, Transform, Sink, Split
from components.sources.demo_rss_source import DemoRSSSource
from components.transformers.prompts import SPAM_DETECTOR
from components.transformers.demo_ai_agent import demo_ai_agent
from components.sinks import JSONLRecorder
from examples.module_05.demo_job_source import DEMO_JOB_FEEDS


# ── Custom prompt for job relevance ──────────────────────────────────────────
# This is the key idea in Module 05: you can define your own prompt.
# Change the target role description to match what YOU are looking for.
# The rest of the app stays exactly the same.

JOB_RELEVANCE_PROMPT = """You are helping a job seeker find relevant postings.

The target role: senior Python engineer or ML engineer, remote or hybrid,
at a well-known tech company working on interesting problems.

Given a job posting title/summary, determine if it is a strong match,
partial match, or not a match for this target role.

Return JSON format:
{
    "match": "STRONG" | "PARTIAL" | "NONE",
    "confidence": 0.0-1.0,
    "reason": "one sentence explanation"
}"""


# ── Demo data source ──────────────────────────────────────────────────────────
# DemoRSSSource normally reads from its own DEMO_FEEDS dict.
# Here we pass in job-specific demo data instead.

class DemoJobSource:
    """Produces demo job postings one at a time, returns None when exhausted."""

    def __init__(self, feed_name, max_articles=None):
        self.articles    = list(DEMO_JOB_FEEDS[feed_name])
        self.max_articles = max_articles or len(self.articles)
        self.index       = 0

    def run(self):
        if self.index >= min(len(self.articles), self.max_articles):
            return None
        article = self.articles[self.index]
        self.index += 1
        return article


# ── Data sources ──────────────────────────────────────────────────────────────
python_src = DemoJobSource(feed_name="python_jobs")
ml_src     = DemoJobSource(feed_name="ml_jobs")


# ── AI components ─────────────────────────────────────────────────────────────
# demo_ai_agent uses keyword matching — no API key needed.
# In app_live.py these become ai_agent(SPAM_DETECTOR) and ai_agent(JOB_RELEVANCE_PROMPT).
spam_detector      = demo_ai_agent(SPAM_DETECTOR)
relevance_checker  = demo_ai_agent(JOB_RELEVANCE_PROMPT)


# ── Sink components ───────────────────────────────────────────────────────────
recorder = JSONLRecorder(path="job_matches.jsonl", mode="w", flush_every=1)

# A sink that silently discards everything — used for the no-match branch.
def discard(msg):
    pass


# ── Transform functions ───────────────────────────────────────────────────────

def filter_spam(text):
    """Drop spam postings before relevance checking."""
    result = spam_detector(text)
    return None if result["is_spam"] else text


def check_relevance(text):
    """
    Check if this posting matches the target role.

    Returns an enriched dict with the original text plus match assessment.
    The routing function below uses the 'match' key to decide where to send it.
    """
    result = relevance_checker(text)
    return {
        "text":       text,
        "match":      result.get("match", "NONE"),
        "confidence": result.get("confidence", 0.0),
        "reason":     result.get("reason", "")
    }


def route_by_match(posting):
    """
    Route matching postings to out_0, non-matching to out_1.

    STRONG and PARTIAL matches go to out_0 (archive + display).
    NONE goes to out_1 (discard sink).
    """
    if posting["match"] in ("STRONG", "PARTIAL"):
        return [posting, None   ]   # → out_0
    else:
        return [None,    posting]   # → out_1


def display_match(posting):
    """Print matching postings to the terminal."""
    icon = "✅" if posting["match"] == "STRONG" else "🔶"
    print(f"  {icon} {posting['match']}: {posting['text']}")
    if posting.get("reason"):
        print(f"       {posting['reason']}")
    print()


# ── Build the network ─────────────────────────────────────────────────────────

python_source = Source(fn=python_src.run,       name="python_jobs")
ml_source     = Source(fn=ml_src.run,           name="ml_jobs")
spam_gate     = Transform(fn=filter_spam,        name="spam_filter")
relevance     = Transform(fn=check_relevance,    name="relevance")
splitter      = Split(fn=route_by_match,         num_outputs=2, name="router")
archive       = Sink(fn=recorder.run,            name="archive")
display       = Sink(fn=display_match,           name="display")
discard_sink  = Sink(fn=discard,                 name="discard")

g = network([
    (python_source,  spam_gate),      # fanin: python_jobs → spam_filter
    (ml_source,      spam_gate),      # fanin: ml_jobs     → spam_filter
    (spam_gate,      relevance),
    (relevance,      splitter),
    (splitter.out_0, archive),        # match   → archive
    (splitter.out_0, display),        # match   → display (fanout from split port)
    (splitter.out_1, discard_sink)    # no-match → discard
])


# ── Run ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print()
    print("💼 Job Postings Monitor")
    print("═" * 60)
    print()
    print("  python_jobs ─┐")
    print("                ├→ spam_filter → relevance → split")
    print("  ml_jobs     ─┘                          → match   → archive + display")
    print("                                          → no_match → dropped")
    print()

    g.run_network()

    print()
    print("═" * 60)
    print("✅ Done! Matches saved to job_matches.jsonl")
    print()
    print("To connect real job feeds and Claude AI, see app_live.py.")
    print("To monitor for your own target role, edit JOB_RELEVANCE_PROMPT.")
    print()
