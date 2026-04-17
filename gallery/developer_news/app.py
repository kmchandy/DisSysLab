# ============================================================
# Developer News Tracker
# Monitors three tech sources for developer-relevant news.
#
# Topology:
#   hacker_news ──┐
#   techcrunch    ┼→ dev_filter → sentiment → ┬→ display
#   bbc_tech ─────┘                            └→ batcher → report
#                                  clock ───────┘
#
# Usage:
#   export ANTHROPIC_API_KEY='your-key'
#   python -m gallery.developer_news.app
# ============================================================

import json
import re
from dissyslab import network
from dissyslab.blocks import Source, Transform, Sink
from dissyslab.components.sources.rss_normalizer import (
    hacker_news, techcrunch, bbc_tech,
)
from dissyslab.components.transformers.ai_agent import ai_agent
from dissyslab.components.transformers.stateful_agent import StatefulAgent
from dissyslab.components.sources.clock_source import ClockSource

# ── Configure Your Interests ──────────────────────────────────
DEV_INTERESTS = [
    "Python",
    "open source",
    "developer tools",
    "APIs",
    "AI coding assistants",
]

INTERESTS_STR = ", ".join(f'"{t}"' for t in DEV_INTERESTS)

# ── Sources ───────────────────────────────────────────────────
hn_feed = hacker_news(max_articles=20, poll_interval=3600)
tc_feed = techcrunch(max_articles=15,  poll_interval=3600)
bbc_feed = bbc_tech(max_articles=15,    poll_interval=3600)

hn_source = Source(fn=hn_feed.run,  name="hacker_news")
tc_source = Source(fn=tc_feed.run,  name="techcrunch")
bbc_source = Source(fn=bbc_feed.run, name="bbc_tech")

# ── AI Agents ─────────────────────────────────────────────────
relevance_agent = ai_agent(f"""
Does this article relate to any of these developer interests: {INTERESTS_STR}?
Return JSON only, no explanation: {{"relevant": true or false, "category": "matched interest or null"}}
""")

sentiment_agent = ai_agent("""
Is this tech article positive, negative, or neutral for software developers?
Return JSON only, no explanation: {"sentiment": "POSITIVE" | "NEGATIVE" | "NEUTRAL", "score": -1.0 to 1.0}
""")

reporter_agent = ai_agent(f"""
You receive a JSON batch of developer news articles grouped by source in by_source.
The reader is interested in: {INTERESTS_STR}.
Write a concise daily digest for a software developer.
Group by category, highlight the most important developments,
and note any stories covered by multiple sources.
Return plain text, not JSON.
""")

# ── Helper ────────────────────────────────────────────────────


def _parse_json(raw):
    """Extract JSON from Claude response, tolerating extra text or pre-parsed dict."""
    if isinstance(raw, dict):
        return raw
    match = re.search(r'\{.*?\}', raw, re.DOTALL)
    return json.loads(match.group()) if match else {}

# ── Transform Functions ───────────────────────────────────────


def filter_dev_news(article):
    if not article.get("text", "").strip():
        return None
    result = _parse_json(relevance_agent(article["text"]))
    if not result.get("relevant"):
        return None
    article["category"] = result.get("category", "")
    return article


def analyze_sentiment(article):
    result = _parse_json(sentiment_agent(article["text"]))
    article["sentiment"] = result.get("sentiment", "NEUTRAL")
    article["score"] = result.get("score", 0.0)
    return article


def display(article):
    icons = {"POSITIVE": "✅", "NEGATIVE": "❌", "NEUTRAL": "➖"}
    icon = icons.get(article["sentiment"], "?")
    print(
        f"{icon} [{article['source']:>12}] [{article['category']}] {article['title']}")
    print(f"        {article['url']}")
    print()


def write_report(batch):
    return {"report": reporter_agent(json.dumps(batch, indent=2))}


def print_report(msg):
    print("\n" + "=" * 70)
    print("DAILY DEVELOPER NEWS DIGEST")
    print(f"Interests: {', '.join(DEV_INTERESTS)}")
    print("=" * 70)
    print(msg["report"])
    print("=" * 70 + "\n")


# ── Batch Reporting ───────────────────────────────────────────
batcher = StatefulAgent(max_articles=200, clear_on_tick=True)
clock = ClockSource.daily()

# ── Build Nodes ───────────────────────────────────────────────
dev_filter = Transform(fn=filter_dev_news,   name="dev_filter")
sentiment = Transform(fn=analyze_sentiment,  name="sentiment")
display_sink = Sink(fn=display,                 name="display")
batcher_node = Transform(fn=batcher.run,        name="batcher")
clock_source = Source(fn=clock.run,             name="clock")
report_node = Transform(fn=write_report,       name="report_writer")
report_sink = Sink(fn=print_report,            name="report_sink")

# ── Network ───────────────────────────────────────────────────
g = network([
    (hn_source,  dev_filter),
    (tc_source,  dev_filter),
    (bbc_source, dev_filter),

    (dev_filter, sentiment),

    (sentiment, display_sink),
    (sentiment, batcher_node),

    (clock_source, batcher_node),
    (batcher_node, report_node),
    (report_node,  report_sink),
])

if __name__ == "__main__":
    print("\n🛠️  Developer News Tracker")
    print(f"   Interests: {', '.join(DEV_INTERESTS)}")
    print("   Sources: Hacker News, TechCrunch, BBC Tech")
    print("   Streaming to console. Daily digest at midnight. Ctrl+C to stop.\n")
    g.run_network(timeout=None)
