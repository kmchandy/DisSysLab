# ============================================================
# AI/ML Research Tracker
# Monitors four tech sources for AI/ML developments.
#
# Topology:
#   hacker_news ────┐
#   mit_tech_review ┤
#   techcrunch      ┼→ ai_filter → sentiment → impact → ┬→ display
#   venturebeat_ai ─┘                                    └→ batcher → report
#                                              clock ────┘
#
# Usage:
#   export ANTHROPIC_API_KEY='your-key'
#   python -m gallery.ai_ml_research.app
# ============================================================

import json
from dsl import network
from dsl.blocks import Source, Transform, Sink
from components.sources.rss_normalizer import (
    hacker_news, mit_tech_review, techcrunch, venturebeat_ai,
)
from components.transformers.ai_agent import ai_agent
from components.transformers.stateful_agent import StatefulAgent
from components.sources.clock_source import ClockSource

# ── Sources ──────────────────────────────────────────────────
hn_feed = hacker_news(max_articles=20,     poll_interval=3600)
mit_feed = mit_tech_review(max_articles=10, poll_interval=3600)
tc_feed = techcrunch(max_articles=10,      poll_interval=3600)
vb_feed = venturebeat_ai(max_articles=10,  poll_interval=3600)

hn_source = Source(fn=hn_feed.run,  name="hacker_news")
mit_source = Source(fn=mit_feed.run, name="mit_tech_review")
tc_source = Source(fn=tc_feed.run,  name="techcrunch")
vb_source = Source(fn=vb_feed.run,  name="venturebeat_ai")

# ── AI Agents ─────────────────────────────────────────────────
relevance_agent = ai_agent("""
Does this article discuss artificial intelligence, machine learning, or LLMs?
Return JSON only, no explanation: {"relevant": true or false}
""")

sentiment_agent = ai_agent("""
Is this AI/ML article positive, negative, or neutral about progress in the field?
Return JSON only, no explanation: {"sentiment": "POSITIVE" | "NEGATIVE" | "NEUTRAL", "score": -1.0 to 1.0}
""")

impact_agent = ai_agent("""
Rate the potential impact of this AI/ML development on the field.
Return JSON only, no explanation: {"impact": "HIGH" | "MEDIUM" | "LOW", "reason": "one sentence"}
""")

reporter_agent = ai_agent("""
You receive a JSON batch of AI/ML articles grouped by source in by_source.
Write a concise daily digest. For each source, list articles grouped by
impact level (HIGH first). Include title and sentiment for each.
Return plain text, not JSON.
""")

# ── Transform Functions ───────────────────────────────────────


def filter_ai_articles(article):
    if not article.get("text", "").strip():
        return None
    raw = relevance_agent(article["text"])
    # print(f"[DEBUG] {repr(raw)}")
    if not raw.strip():
        return None
    result = json.loads(raw)
    if not result["relevant"]:
        return None
    return article


def analyze_sentiment(article):
    result = json.loads(sentiment_agent(article["text"]))
    article["sentiment"] = result["sentiment"]
    article["score"] = result["score"]
    return article


def rate_impact(article):
    result = json.loads(impact_agent(article["text"]))
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
    return {"report": reporter_agent(json.dumps(batch, indent=2))}


def print_report(msg):
    print("\n" + "=" * 70)
    print("DAILY AI/ML DIGEST")
    print("=" * 70)
    print(msg["report"])
    print("=" * 70 + "\n")


# ── Batch Reporting ───────────────────────────────────────────
batcher = StatefulAgent(max_articles=200, clear_on_tick=True)
clock = ClockSource.daily()

# ── Build Nodes ───────────────────────────────────────────────
ai_filter = Transform(fn=filter_ai_articles, name="ai_filter")
sentiment = Transform(fn=analyze_sentiment,  name="sentiment")
impact = Transform(fn=rate_impact,        name="impact")
display_sink = Sink(fn=display,                 name="display")
batcher_node = Transform(fn=batcher.run,        name="batcher")
clock_source = Source(fn=clock.run,             name="clock")
report_node = Transform(fn=write_report,       name="report_writer")
report_sink = Sink(fn=print_report,            name="report_sink")

# ── Network ───────────────────────────────────────────────────
g = network([
    (hn_source,  ai_filter),
    (mit_source, ai_filter),
    (tc_source,  ai_filter),
    (vb_source,  ai_filter),

    (ai_filter, sentiment),
    (sentiment, impact),

    (impact, display_sink),
    (impact, batcher_node),

    (clock_source, batcher_node),
    (batcher_node, report_node),
    (report_node,  report_sink),
])

if __name__ == "__main__":
    print("\n🤖 AI/ML Research Tracker")
    print("   Sources: Hacker News, MIT Tech Review, TechCrunch, VentureBeat AI")
    print("   Streaming to console. Daily digest at midnight. Ctrl+C to stop.\n")
    g.run_network(timeout=None)
