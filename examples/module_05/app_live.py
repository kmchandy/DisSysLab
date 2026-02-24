# examples/module_05/app_live.py

"""
Module 05: Job Postings Monitor — Real RSS Feeds + Real Claude AI

This is app.py connected to live job RSS feeds and the real Claude API.
The network topology and all functions are identical to app.py.
The only changes are the source (RSSSource instead of DemoJobSource)
and the AI agent (ai_agent instead of demo_ai_agent).

IMPORTANT — Customize your target role before running:
  Find JOB_RELEVANCE_PROMPT below and edit the target role description
  to match what YOU are actually looking for. This is the only change
  you need to make to personalize the monitor.

Setup:
    pip install feedparser
    export ANTHROPIC_API_KEY='your-key-here'

Run from the DisSysLab root directory:
    python3 -m examples.module_05.app_live

max_articles=5 per feed keeps API costs low during testing.
Remove the limit or increase it once you're happy with the results.
"""

import re
from dsl import network
from dsl.blocks import Source, Transform, Sink, Split
from components.sources.rss_source import RSSSource           # ← real RSS
from components.transformers.prompts import SPAM_DETECTOR
from components.transformers.ai_agent import ai_agent         # ← real Claude
from components.sinks import JSONLRecorder


# ── Customize this prompt for your target role ────────────────────────────────
# This is the only thing you need to change to personalize the monitor.
# Describe your ideal job: role, location, salary, tech stack, company type.

JOB_RELEVANCE_PROMPT = """You are helping a job seeker find relevant postings.

The target role: senior Python engineer or ML engineer, remote or hybrid,
$150k+ at a well-known tech company working on interesting problems.
Strong preference for roles involving distributed systems, AI, or data.

Given a job posting title/summary, determine if it is a strong match,
partial match, or not a match for this target role.

Return JSON format:
{
    "match": "STRONG" | "PARTIAL" | "NONE",
    "confidence": 0.0-1.0,
    "reason": "one sentence explanation"
}"""


# ── Real RSS feeds ────────────────────────────────────────────────────────────
# max_articles=5 to limit API costs during testing. Remove or increase to taste.
# These are public feeds that require no authentication.

python_rss = RSSSource(
    "https://www.indeed.com/rss?q=python+engineer&l=remote",
    max_articles=5
)
ml_rss = RSSSource(
    "https://remoteok.io/remote-machine-learning-jobs.rss",
    max_articles=5
)


# ── Real AI agents ────────────────────────────────────────────────────────────
spam_detector     = ai_agent(SPAM_DETECTOR)
relevance_checker = ai_agent(JOB_RELEVANCE_PROMPT)


# ── Sink components ───────────────────────────────────────────────────────────
recorder = JSONLRecorder(path="job_matches_live.jsonl", mode="w", flush_every=1)


def discard(msg):
    pass


# ── Transform functions ───────────────────────────────────────────────────────
# Identical to app.py — nothing changes here.

def filter_spam(text):
    """Drop spam postings before relevance checking."""
    result = spam_detector(text)
    return None if result["is_spam"] else text


def check_relevance(text):
    """Check if this posting matches the target role."""
    result = relevance_checker(text)
    return {
        "text":       text,
        "match":      result.get("match", "NONE"),
        "confidence": result.get("confidence", 0.0),
        "reason":     result.get("reason", "")
    }


def route_by_match(posting):
    """Route matches to out_0, non-matches to out_1."""
    if posting["match"] in ("STRONG", "PARTIAL"):
        return [posting, None   ]
    else:
        return [None,    posting]


def display_match(posting):
    """Print matching postings to the terminal."""
    icon = "✅" if posting["match"] == "STRONG" else "🔶"
    print(f"  {icon} {posting['match']}: {posting['text']}")
    if posting.get("reason"):
        print(f"       {posting['reason']}")
    print()


# ── Build the network ─────────────────────────────────────────────────────────
# Identical to app.py — nothing changes here.

python_source = Source(fn=python_rss.run,    name="python_jobs")
ml_source     = Source(fn=ml_rss.run,        name="ml_jobs")
spam_gate     = Transform(fn=filter_spam,     name="spam_filter")
relevance     = Transform(fn=check_relevance, name="relevance")
splitter      = Split(fn=route_by_match,      num_outputs=2, name="router")
archive       = Sink(fn=recorder.run,         name="archive")
display       = Sink(fn=display_match,        name="display")
discard_sink  = Sink(fn=discard,              name="discard")

g = network([
    (python_source,  spam_gate),
    (ml_source,      spam_gate),
    (spam_gate,      relevance),
    (relevance,      splitter),
    (splitter.out_0, archive),
    (splitter.out_0, display),
    (splitter.out_1, discard_sink)
])


# ── Run ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print()
    print("💼 Job Postings Monitor — Real RSS Feeds + Claude AI")
    print("═" * 60)
    print()
    print("  python_jobs ─┐")
    print("                ├→ spam_filter → relevance → split")
    print("  ml_jobs     ─┘                          → match   → archive + display")
    print("                                          → no_match → dropped")
    print()
    print("  (Reading live RSS feeds — first fetch may take a moment)")
    print("  (max_articles=5 per feed to keep API costs low)")
    print()

    g.run_network(timeout=120)

    print()
    print("═" * 60)
    print("✅ Done! Matches saved to job_matches_live.jsonl")
    print()
    print("To monitor for your own role, edit JOB_RELEVANCE_PROMPT.")
    print("To see more postings, increase max_articles in the RSSSource calls.")
    print()
