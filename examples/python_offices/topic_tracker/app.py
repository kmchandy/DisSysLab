# ============================================================
# Topic Tracker
# Monitors three international news sources for user-specified topics.
#
# Topology:
#   aljazeera ──┐
#   npr         ┼→ topic_filter → sentiment → ┬→ display
#   bbc_world ──┘                              └→ batcher → report
#                                   clock ─────┘
#
# Usage:
#   export ANTHROPIC_API_KEY='your-key'
#   python -m gallery.topic_tracker.app
# ============================================================

import json
import re
from dissyslab import network
from dissyslab.blocks import Source, Transform, Sink
from dissyslab.components.sources.rss_normalizer import (
    al_jazeera, npr_news, bbc_world,
)
from dissyslab.components.transformers.ai_agent import ai_agent
from dissyslab.components.transformers.stateful_agent import StatefulAgent
from dissyslab.components.sources.clock_source import ClockSource

# ── Configure Your Topics ─────────────────────────────────────
TOPICS = [
    "climate change",
    "artificial intelligence",
    "US elections",
]

TOPICS_STR = ", ".join(f'"{t}"' for t in TOPICS)

# ── Sources ───────────────────────────────────────────────────
aj_feed = al_jazeera(max_articles=15, poll_interval=3600)
npr_feed = npr_news(max_articles=15,   poll_interval=3600)
bbc_feed = bbc_world(max_articles=15,  poll_interval=3600)

aj_source = Source(fn=aj_feed.run,  name="al_jazeera")
npr_source = Source(fn=npr_feed.run, name="npr_news")
bbc_source = Source(fn=bbc_feed.run, name="bbc_world")

# ── AI Agents ─────────────────────────────────────────────────
relevance_agent = ai_agent(f"""
Does this article discuss any of these topics: {TOPICS_STR}?
Return JSON only, no explanation: {{"relevant": true or false, "topic": "matched topic or null"}}
""")

sentiment_agent = ai_agent("""
What is the overall tone of this article?
Return JSON only, no explanation: {"sentiment": "POSITIVE" | "NEGATIVE" | "NEUTRAL", "score": -1.0 to 1.0}
""")

reporter_agent = ai_agent(f"""
You receive a JSON batch of news articles grouped by source in by_source.
The articles cover these topics: {TOPICS_STR}.
Write a concise digest comparing how different outlets cover each topic.
For each topic, note which sources covered it and whether their framing differs.
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


def filter_by_topic(article):
    if not article.get("text", "").strip():
        return None
    result = _parse_json(relevance_agent(article["text"]))
    if not result.get("relevant"):
        return None
    article["topic"] = result.get("topic", "")
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
        f"{icon} [{article['source']:>10}] [{article['topic']}] {article['title']}")
    print(f"        {article['url']}")
    print()


def write_report(batch):
    return {"report": reporter_agent(json.dumps(batch, indent=2))}


def print_report(msg):
    print("\n" + "=" * 70)
    print("TOPIC TRACKER DIGEST")
    print(f"Topics: {', '.join(TOPICS)}")
    print("=" * 70)
    print(msg["report"])
    print("=" * 70 + "\n")


# ── Batch Reporting ───────────────────────────────────────────
batcher = StatefulAgent(max_articles=200, clear_on_tick=True)
clock = ClockSource.daily()

# ── Build Nodes ───────────────────────────────────────────────
topic_filter = Transform(fn=filter_by_topic,  name="topic_filter")
sentiment = Transform(fn=analyze_sentiment, name="sentiment")
display_sink = Sink(fn=display,                name="display")
batcher_node = Transform(fn=batcher.run,       name="batcher")
clock_source = Source(fn=clock.run,            name="clock")
report_node = Transform(fn=write_report,      name="report_writer")
report_sink = Sink(fn=print_report,           name="report_sink")

# ── Network ───────────────────────────────────────────────────
g = network([
    (aj_source,  topic_filter),
    (npr_source, topic_filter),
    (bbc_source, topic_filter),

    (topic_filter, sentiment),

    (sentiment, display_sink),
    (sentiment, batcher_node),

    (clock_source,  batcher_node),
    (batcher_node,  report_node),
    (report_node,   report_sink),
])

if __name__ == "__main__":
    print("\n📰 Topic Tracker")
    print(f"   Topics: {', '.join(TOPICS)}")
    print("   Sources: Al Jazeera, NPR, BBC World")
    print("   Streaming to console. Daily digest at midnight. Ctrl+C to stop.\n")
    g.run_network(timeout=None)
