# examples/module_05/app.py

"""
Module 05: Job Postings Monitor — Demo Version

Monitors two demo job feeds, filters spam, checks relevance using a
demo AI agent, and routes matching postings to archive + display.

Network topology:
    python_jobs ─┐
                  ├→ spam_filter → relevance → split → out_0 → archive
    ml_jobs     ─┘                                          → out_0 → display
                                                  → out_1 → (discard)

No API keys needed. Uses demo job data and demo AI components.
To connect real RSS feeds and Claude AI, see app_live.py.

Run from the DisSysLab root directory:
    python3 -m examples.module_05.app
"""

from dsl import network
from dsl.blocks import Source, Transform, Sink, Split
from components.sources.demo_job_source import DemoJobSource
from components.transformers.prompts import SPAM_DETECTOR, JOB_DETECTOR
from components.transformers.demo_ai_agent import demo_ai_agent
from components.sinks import JSONLRecorder


# ── Data sources ──────────────────────────────────────────────────────────────
python_src = DemoJobSource(feed_name="python_jobs")
ml_src = DemoJobSource(feed_name="ml_jobs")


# ── AI components ─────────────────────────────────────────────────────────────
# demo_ai_agent uses keyword matching — no API key needed.
# In app_live.py these become ai_agent(SPAM_DETECTOR) and ai_agent(JOB_DETECTOR).
spam_detector = demo_ai_agent(SPAM_DETECTOR)
relevance_checker = demo_ai_agent(JOB_DETECTOR)


# ── Sink components ───────────────────────────────────────────────────────────
recorder = JSONLRecorder(path="job_matches.jsonl", mode="w", flush_every=1)


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

    To personalize for your own job search, edit JOB_DETECTOR in:
        components/transformers/prompts.py
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
        return [posting, None]   # → out_0
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

python_source = Source(fn=python_src.run,        name="python_jobs")
ml_source = Source(fn=ml_src.run,            name="ml_jobs")
spam_gate = Transform(fn=filter_spam,         name="spam_filter")
relevance = Transform(fn=check_relevance,     name="relevance")
splitter = Split(fn=route_by_match,          num_outputs=2, name="router")
archive = Sink(fn=recorder.run,             name="archive")
display = Sink(fn=display_match,            name="display")
discard_sink = Sink(fn=discard,                  name="discard")

g = network([
    (python_source,  spam_gate),      # fanin: python_jobs → spam_filter
    (ml_source,      spam_gate),      # fanin: ml_jobs     → spam_filter
    (spam_gate,      relevance),
    (relevance,      splitter),
    (splitter.out_0, archive),        # match   → archive
    (splitter.out_0, display),        # match   → display (fanout from split port)
    (splitter.out_1, discard_sink),   # no-match → discard
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
    print("To use real job feeds and Claude AI, see app_live.py.")
    print("To monitor for your own target role, edit JOB_DETECTOR in prompts.py.")
    print()
