# ============================================================
# Climate Monitor
# Monitors three sources for climate and environment news.
#
# Topology:
#   nasa_news ──┐
#   bbc_tech    ┼→ climate_filter → sentiment → ┬→ display
#   npr_news ───┘                                └→ batcher → report
#                                    clock ───────┘
#
# Usage:
#   export ANTHROPIC_API_KEY='your-key'
#   python -m gallery.climate_monitor.app
# ============================================================

import json
from dsl import network
from dsl.blocks import Source, Transform, Sink
from components.sources.rss_normalizer import (
    nasa_news, bbc_tech, npr_news,
)
from components.transformers.ai_agent import ai_agent
from components.transformers.stateful_agent import StatefulAgent
from components.sources.clock_source import ClockSource

# ── Configure Your Interests ──────────────────────────────────
CLIMATE_TOPICS = [
    "climate change",
    "renewable energy",
    "carbon emissions",
    "extreme weather",
    "biodiversity",
]

TOPICS_STR = ", ".join(f'"{t}"' for t in CLIMATE_TOPICS)

# ── Sources ───────────────────────────────────────────────────
nasa_feed = nasa_news(max_articles=10, poll_interval=3600)
bbc_feed = bbc_tech(max_articles=15,  poll_interval=3600)
npr_feed = npr_news(max_articles=15,  poll_interval=3600)

nasa_source = Source(fn=nasa_feed.run, name="nasa")
bbc_source = Source(fn=bbc_feed.run,  name="bbc_tech")
npr_source = Source(fn=npr_feed.run,  name="npr_news")

# ── AI Agents ─────────────────────────────────────────────────
relevance_agent = ai_agent(f"""
Does this article relate to any of these climate topics: {TOPICS_STR}?
Return JSON only, no explanation: {{"relevant": true or false, "topic": "matched topic or null"}}
""")

sentiment_agent = ai_agent("""
Is this climate article positive, negative, or neutral in its outlook
for the planet and humanity's response to climate change?
Return JSON only, no explanation: {"sentiment": "POSITIVE" | "NEGATIVE" | "NEUTRAL", "score": -1.0 to 1.0}
""")

reporter_agent = ai_agent(f"""
You receive a JSON batch of climate news articles grouped by source in by_source.
Topics covered: {TOPICS_STR}.
Write a concise daily climate digest.
Group by topic. Note whether the overall news today is encouraging or concerning.
Highlight any stories covered by multiple sources.
Return plain text, not JSON.
""")

# ── Transform Functions ───────────────────────────────────────


def filter_climate_news(article):
    if not article.get("text", "").strip():
        return None
    raw = relevance_agent(article["text"])
    if not raw.strip():
        return None
    result = json.loads(raw)
    if not result["relevant"]:
        return None
    article["topic"] = result["topic"]
    return article


def analyze_sentiment(article):
    result = json.loads(sentiment_agent(article["text"]))
    article["sentiment"] = result["sentiment"]
    article["score"] = result["score"]
    return article


def display(article):
    icons = {"POSITIVE": "🌱", "NEGATIVE": "🌊", "NEUTRAL": "➖"}
    icon = icons.get(article["sentiment"], "?")
    print(
        f"{icon} [{article['source']:>10}] [{article['topic']}] {article['title']}")
    print(f"        {article['url']}")
    print()


def write_report(batch):
    return {"report": reporter_agent(json.dumps(batch, indent=2))}


def print_report(msg):
    print("\n" + "=" * 70)
    print("DAILY CLIMATE DIGEST")
    print(f"Topics: {', '.join(CLIMATE_TOPICS)}")
    print("=" * 70)
    print(msg["report"])
    print("=" * 70 + "\n")


# ── Batch Reporting ───────────────────────────────────────────
batcher = StatefulAgent(max_articles=200, clear_on_tick=True)
clock = ClockSource.daily()

# ── Build Nodes ───────────────────────────────────────────────
climate_filter = Transform(fn=filter_climate_news, name="climate_filter")
sentiment = Transform(fn=analyze_sentiment,    name="sentiment")
display_sink = Sink(fn=display,                   name="display")
batcher_node = Transform(fn=batcher.run,          name="batcher")
clock_source = Source(fn=clock.run,               name="clock")
report_node = Transform(fn=write_report,         name="report_writer")
report_sink = Sink(fn=print_report,              name="report_sink")

# ── Network ───────────────────────────────────────────────────
g = network([
    (nasa_source, climate_filter),
    (bbc_source,  climate_filter),
    (npr_source,  climate_filter),

    (climate_filter, sentiment),

    (sentiment, display_sink),
    (sentiment, batcher_node),

    (clock_source, batcher_node),
    (batcher_node, report_node),
    (report_node,  report_sink),
])

if __name__ == "__main__":
    print("\n🌍 Climate Monitor")
    print(f"   Topics: {', '.join(CLIMATE_TOPICS)}")
    print("   Sources: NASA, BBC Tech, NPR")
    print("   Streaming to console. Daily digest at midnight. Ctrl+C to stop.\n")
    g.run_network(timeout=None)
