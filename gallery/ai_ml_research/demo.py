# ============================================================
# AI/ML Research Tracker — Demo Version
# Uses prepackaged articles and AI responses.
# No API key needed. No network calls. Run this first.
#
# Usage:
#   python -m gallery.ai_ml_research.demo
# ============================================================

import json
from dsl import network
from dsl.blocks import Source, Transform, Sink
from gallery.ai_ml_research.demo_data import (
    ARTICLES, RELEVANCE, SENTIMENT, IMPACT, REPORT, lookup
)


# ── Demo Sources ──────────────────────────────────────────────
def make_article_source(articles):
    """Generator that yields prepackaged articles one by one."""
    def _run():
        for article in articles:
            yield article
    return _run


# ── Demo AI Agents ────────────────────────────────────────────
def demo_relevance(text):
    return lookup(RELEVANCE, text)


def demo_sentiment(text):
    return lookup(SENTIMENT, text)


def demo_impact(text):
    return lookup(IMPACT, text)


def demo_reporter(batch_json):
    return REPORT


# ── Transform Functions ───────────────────────────────────────
def filter_ai_articles(article):
    if not article.get("text", "").strip():
        return None
    raw = demo_relevance(article["title"])
    result = json.loads(raw)
    if not result["relevant"]:
        return None
    return article


def analyze_sentiment(article):
    result = json.loads(demo_sentiment(article["title"]))
    article["sentiment"] = result["sentiment"]
    article["score"] = result["score"]
    return article


def rate_impact(article):
    result = json.loads(demo_impact(article["title"]))
    article["impact"] = result["impact"]
    article["reason"] = result["reason"]
    return article


def display(article):
    icons = {"POSITIVE": "✅", "NEGATIVE": "❌", "NEUTRAL": "➖"}
    stars = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}
    icon = icons.get(article["sentiment"], "?")
    star = stars.get(article["impact"], "?")
    print(f"{icon}{star} [{article['source']:>15}] {article['title']}")
    print(f"         {article['url']}")
    print()


def write_report(batch):
    return {"report": demo_reporter(json.dumps(batch))}


def print_report(msg):
    print("\n" + "=" * 70)
    print("DAILY AI/ML DIGEST  [demo]")
    print("=" * 70)
    print(msg["report"])
    print("=" * 70 + "\n")


# ── Single-batch batcher for demo ────────────────────────────
collected = []


def collect(article):
    collected.append(article)
    return article


def emit_report(_tick):
    if not collected:
        return None
    batch = {"by_source": {}}
    for a in collected:
        batch["by_source"].setdefault(a["source"], []).append(a)
    return batch


# ── Build Network ─────────────────────────────────────────────
article_source = Source(fn=make_article_source(ARTICLES), name="articles")

ai_filter = Transform(fn=filter_ai_articles, name="ai_filter")
sentiment = Transform(fn=analyze_sentiment,   name="sentiment")
impact = Transform(fn=rate_impact,         name="impact")
collector = Sink(fn=collect,             name="collector")
display_sink = Sink(fn=display,                  name="display")

# Simple end-of-run report using a trigger article
trigger_source = Source(fn=make_article_source(
    [{"_trigger": True}]), name="trigger")
batcher_node = Transform(fn=emit_report,  name="batcher")
report_node = Transform(fn=write_report, name="report_writer")
report_sink = Sink(fn=print_report,      name="report_sink")

g = network([
    (article_source, ai_filter),
    (ai_filter,      sentiment),
    (sentiment,      impact),
    (impact,         collector),
    (impact,         display_sink),

    (trigger_source, batcher_node),
    (batcher_node,   report_node),
    (report_node,    report_sink),
])

if __name__ == "__main__":
    print("\n🤖 AI/ML Research Tracker  [DEMO — no API key needed]")
    print("   Sources: Hacker News, MIT Tech Review, TechCrunch, VentureBeat AI")
    print("   Using prepackaged articles and AI responses.\n")
    g.run_network(timeout=10)
    print("\n▶  To run with live data:  python -m gallery.ai_ml_research.app\n")
