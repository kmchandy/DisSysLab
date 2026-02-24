# examples/module_05/app_extended.py

"""
Module 05: Job Postings Monitor — Extended App

This extends app.py by adding salary extraction after the relevance check.
Matching postings are enriched with salary information (if mentioned) before
being saved to the archive.

Network topology:
    python_jobs ─┐
                  ├→ spam_filter → relevance → salary → split → out_0 → archive
    ml_jobs     ─┘                                           → out_0 → display
                                                             → out_1 → discard

The salary extractor adds a "salary" key to each posting dict.
Postings without salary information get salary: null.

Run from the DisSysLab root directory:
    python3 -m examples.module_05.app_extended
"""

from dsl import network
from dsl.blocks import Source, Transform, Sink, Split
from components.transformers.prompts import SPAM_DETECTOR
from components.transformers.demo_ai_agent import demo_ai_agent
from components.sinks import JSONLRecorder
from examples.module_05.demo_job_source import DEMO_JOB_FEEDS


# ── Custom prompts ────────────────────────────────────────────────────────────

JOB_RELEVANCE_PROMPT = """You are helping a job seeker find relevant postings.

The target role: senior Python engineer or ML engineer, remote or hybrid,
at a well-known tech company working on interesting problems.

Return JSON format:
{
    "match": "STRONG" | "PARTIAL" | "NONE",
    "confidence": 0.0-1.0,
    "reason": "one sentence explanation"
}"""

SALARY_EXTRACTOR_PROMPT = """Extract salary information from the given job posting text.

Look for salary ranges, hourly rates, or compensation mentions.
If no salary information is present, return null for all fields.

Return JSON format:
{
    "salary_mentioned": true | false,
    "salary_text": "the salary text as written, or null",
    "min_salary": integer in USD/year or null,
    "max_salary": integer in USD/year or null
}"""


# ── Demo data source ──────────────────────────────────────────────────────────

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


# ── Data sources ──────────────────────────────────────────────────────────────
python_src = DemoJobSource(feed_name="python_jobs")
ml_src     = DemoJobSource(feed_name="ml_jobs")


# ── AI components ─────────────────────────────────────────────────────────────
spam_detector      = demo_ai_agent(SPAM_DETECTOR)
relevance_checker  = demo_ai_agent(JOB_RELEVANCE_PROMPT)
salary_extractor   = demo_ai_agent(SALARY_EXTRACTOR_PROMPT)


# ── Sink components ───────────────────────────────────────────────────────────
recorder = JSONLRecorder(path="job_matches_extended.jsonl", mode="w", flush_every=1)


def discard(msg):
    pass


# ── Transform functions ───────────────────────────────────────────────────────

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


def extract_salary(posting):
    """
    Add salary information to the posting dict.

    This runs on ALL postings, before routing — salary is extracted
    whether or not the posting will match. Routing happens next.
    Only matching postings ever reach the archive, so only their
    salary data gets saved.
    """
    result = salary_extractor(posting["text"])
    posting["salary_mentioned"] = result.get("salary_mentioned", False)
    posting["salary_text"]      = result.get("salary_text", None)
    posting["min_salary"]       = result.get("min_salary", None)
    posting["max_salary"]       = result.get("max_salary", None)
    return posting


def route_by_match(posting):
    if posting["match"] in ("STRONG", "PARTIAL"):
        return [posting, None   ]
    else:
        return [None,    posting]


def display_match(posting):
    icon = "✅" if posting["match"] == "STRONG" else "🔶"
    print(f"  {icon} {posting['match']}: {posting['text']}")
    if posting.get("salary_text"):
        print(f"       💰 {posting['salary_text']}")
    if posting.get("reason"):
        print(f"       {posting['reason']}")
    print()


# ── Build the network ─────────────────────────────────────────────────────────

python_source = Source(fn=python_src.run,    name="python_jobs")
ml_source     = Source(fn=ml_src.run,        name="ml_jobs")
spam_gate     = Transform(fn=filter_spam,     name="spam_filter")
relevance     = Transform(fn=check_relevance, name="relevance")
salary        = Transform(fn=extract_salary,  name="salary")
splitter      = Split(fn=route_by_match,      num_outputs=2, name="router")
archive       = Sink(fn=recorder.run,         name="archive")
display       = Sink(fn=display_match,        name="display")
discard_sink  = Sink(fn=discard,              name="discard")

g = network([
    (python_source,  spam_gate),
    (ml_source,      spam_gate),
    (spam_gate,      relevance),
    (relevance,      salary),          # new: salary extracted before routing
    (salary,         splitter),
    (splitter.out_0, archive),
    (splitter.out_0, display),
    (splitter.out_1, discard_sink)
])


# ── Run ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print()
    print("💼 Job Postings Monitor — With Salary Extraction")
    print("═" * 60)
    print()
    print("  python_jobs ─┐")
    print("                ├→ spam_filter → relevance → salary → split")
    print("  ml_jobs     ─┘                                   → match → archive + display")
    print("                                                   → no_match → dropped")
    print()

    g.run_network()

    print()
    print("═" * 60)
    print("✅ Done! Matches (with salary) saved to job_matches_extended.jsonl")
    print()
