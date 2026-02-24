# examples/module_05/claude_generated_app.py

"""
This is the unedited output Claude produced when given this prompt:

    "Build me a DisSysLab job monitor that reads from two demo job feeds
    (python_jobs and ml_jobs), filters spam, checks if each posting matches
    a target role of senior Python or ML engineer at a tech company, and
    routes matches to a file and display. Non-matches are dropped.
    Use demo components."

It runs identically to app.py. Compare the two files to see what Claude
generates versus the hand-commented teaching version.

Run from the DisSysLab root directory:
    python3 -m examples.module_05.claude_generated_app
"""

# Job Postings Monitor
# Topology: python_jobs ─┐
#                          ├→ spam_filter → relevance → split → out_0 → archive
#           ml_jobs      ─┘                                  → out_0 → display
#                                                            → out_1 → discard

from dsl import network
from dsl.blocks import Source, Transform, Sink, Split
from components.transformers.prompts import SPAM_DETECTOR
from components.transformers.demo_ai_agent import demo_ai_agent
from components.sinks import JSONLRecorder
from examples.module_05.demo_job_source import DEMO_JOB_FEEDS


JOB_RELEVANCE_PROMPT = """You are helping a job seeker find relevant postings.

The target role: senior Python engineer or ML engineer, remote or hybrid,
at a well-known tech company working on interesting problems.

Return JSON format:
{
    "match": "STRONG" | "PARTIAL" | "NONE",
    "confidence": 0.0-1.0,
    "reason": "one sentence explanation"
}"""


class DemoJobSource:
    def __init__(self, feed_name, max_articles=None):
        self.articles     = list(DEMO_JOB_FEEDS[feed_name])
        self.max_articles = max_articles or len(self.articles)
        self.index        = 0

    def run(self):
        if self.index >= min(len(self.articles), self.max_articles):
            return None
        article = self.articles[self.index]
        self.index += 1
        return article


python_src = DemoJobSource(feed_name="python_jobs")
ml_src     = DemoJobSource(feed_name="ml_jobs")

spam_detector     = demo_ai_agent(SPAM_DETECTOR)
relevance_checker = demo_ai_agent(JOB_RELEVANCE_PROMPT)

recorder = JSONLRecorder(path="my_job_matches.jsonl", mode="w", flush_every=1)


def filter_spam(text):
    result = spam_detector(text)
    return None if result["is_spam"] else text


def check_relevance(text):
    result = relevance_checker(text)
    return {
        "text":       text,
        "match":      result.get("match", "NONE"),
        "confidence": result.get("confidence", 0.0),
        "reason":     result.get("reason", "")
    }


def route_by_match(posting):
    if posting["match"] in ("STRONG", "PARTIAL"):
        return [posting, None   ]
    else:
        return [None,    posting]


def display_match(posting):
    icon = "✅" if posting["match"] == "STRONG" else "🔶"
    print(f"  {icon} {posting['match']}: {posting['text']}")


def discard(msg):
    pass


python_source = Source(fn=python_src.run,    name="python_jobs")
ml_source     = Source(fn=ml_src.run,        name="ml_jobs")
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
    print("✅ Done! Matches saved to my_job_matches.jsonl")
    print()
